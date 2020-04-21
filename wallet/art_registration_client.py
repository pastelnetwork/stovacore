import uuid
import asyncio
from datetime import datetime

from cnode_connection import get_blockchain_connection
from core_modules.ticket_models import RegistrationTicket, Signature, ImageData
from core_modules.settings import NetWorkSettings
from core_modules.helpers import require_true
from core_modules.logger import initlogging
from utils.mn_ordering import get_masternode_ordering
from wallet.database import RegticketDB

art_reg_client_logger = initlogging('Logger', __name__)


class ArtRegistrationClient:
    def __init__(self, chainwrapper):
        self.__chainwrapper = chainwrapper

    def __generate_signed_ticket(self, ticket):
        signed_ticket = Signature(dictionary={
            "signature": get_blockchain_connection().pastelid_sign(ticket.serialize()),
            "pastelid": get_blockchain_connection().pastelid
        })

        # make sure we validate correctly
        signed_ticket.validate(ticket)
        return signed_ticket

    @classmethod
    def generate_regticket(cls, image_data: bytes, regticket_data: dict):
        image = ImageData(dictionary={
            "image": image_data,
            "lubychunks": ImageData.generate_luby_chunks(image_data),
            "thumbnail": ImageData.generate_thumbnail(image_data),
        })

        image.validate()
        blocknum = get_blockchain_connection().getblockcount()
        return RegistrationTicket(dictionary={
            "artist_name": regticket_data.get('artist_name', ''),
            "artist_website": regticket_data.get('artist_website', ''),
            "artist_written_statement": regticket_data.get('artist_written_statement', ''),

            "artwork_title": regticket_data.get('artwork_title', ''),
            "artwork_series_name": regticket_data.get('artwork_series_name', ''),
            "artwork_creation_video_youtube_url": regticket_data.get('artwork_creation_video_youtube_url', ''),
            "artwork_keyword_set": regticket_data.get('artwork_keyword_set', ''),
            "total_copies": int(regticket_data.get('total_copies', 0)),
            # "copy_price": copy_price,

            "fingerprints": image.generate_fingerprints(),
            "lubyhashes": image.get_luby_hashes(),
            "lubyseeds": image.get_luby_seeds(),
            "thumbnailhash": image.get_thumbnail_hash(),

            "author": get_blockchain_connection().pastelid,
            "order_block_txid": get_blockchain_connection().getbestblockhash(),
            "blocknum": blocknum,
            "imagedata_hash": image.get_artwork_hash(),
        })

    async def get_workers_fee(self, image_data, regticket):
        regticket_signature = self.__generate_signed_ticket(regticket)

        regticket_db = RegticketDB.create(created=datetime.now(), blocknum=regticket.blocknum,
                                          serialized_regticket=regticket.serialize(),
                                          serialized_signature=regticket_signature.serialize(),
                                          image_hash=regticket.imagedata_hash)

        mn0 = get_masternode_ordering()[0]
        art_reg_client_logger.debug('Top masternode received: {}'.format(mn0.server_ip))
        upload_code = await mn0.call_masternode("REGTICKET_REQ", "REGTICKET_RESP",
                                                [regticket.serialize(), regticket_signature.serialize()])
        worker_fee = await mn0.call_masternode("IMAGE_UPLOAD_MN0_REQ", "IMAGE_UPLOAD_MN0_RESP",
                                               {'image_data': image_data, 'upload_code': upload_code})
        regticket_db.worker_fee = worker_fee
        regticket_db.upload_code_mn0 = upload_code
        regticket_db.save()
        return {'regticket_id': regticket_db.id, 'worker_fee': worker_fee}

    async def send_regticket_to_mn2_mn3(self, regticket_id):
        regticket_db = RegticketDB.get(RegticketDB.id == regticket_id)
        with open(regticket_db.path_to_image, 'rb') as f:
            image_data = f.read()

        mn0, mn1, mn2 = get_masternode_ordering(regticket_db.blocknum)[:3]

        async def send_regticket_to_mn(mn, serialized_regticket, serialized_signature, img_data):
            """
            Here we push ticket to given masternode, receive upload_code, then push image.
            Masternode will return fee, but we ignore it here.
            """
            try:
                upload_code = await mn.call_masternode("REGTICKET_REQ", "REGTICKET_RESP",
                                                       [serialized_regticket, serialized_signature])
                worker_fee = await mn.call_masternode("IMAGE_UPLOAD_REQ", "IMAGE_UPLOAD_RESP",
                                                      {'image_data': img_data, 'upload_code': upload_code})
            except Exception as ex:
                return None, str(ex)
            return upload_code, None

        result_mn1, result_mn2 = await asyncio.gather(
            send_regticket_to_mn(mn1, regticket_db.serialized_regticket, regticket_db.serialized_signature, image_data),
            send_regticket_to_mn(mn2, regticket_db.serialized_regticket, regticket_db.serialized_signature, image_data),
            return_exceptions=True
        )
        upload_code_mn1, err_mn1 = result_mn1
        upload_code_mn2, err_mn2 = result_mn2
        art_reg_client_logger.warn('Upload code1: {}'.format(upload_code_mn1))
        art_reg_client_logger.warn('Upload code2: {}'.format(upload_code_mn2))
        if not upload_code_mn1:
            return False, err_mn1
        if not upload_code_mn2:
            return False, err_mn2
        regticket_db.upload_code_mn1 = upload_code_mn1
        regticket_db.upload_code_mn2 = upload_code_mn2
        regticket_db.save()
        return True, None
