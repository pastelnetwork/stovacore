import uuid
import asyncio
from datetime import datetime

from core_modules.ticket_models import RegistrationTicket, Signature, FinalRegistrationTicket, ActivationTicket, \
    FinalActivationTicket, ImageData
from PastelCommon.signatures import pastel_id_write_signature_on_data_func
from core_modules.settings import NetWorkSettings
from core_modules.helpers import require_true
from core_modules.logger import initlogging
from wallet.database import RegticketDB

art_reg_client_logger = initlogging('Logger', __name__)


class ArtRegistrationClient:
    def __init__(self, privkey, pubkey, chainwrapper, nodemanager):
        self.__chainwrapper = chainwrapper
        self.__nodemanager = nodemanager

        # get MN ordering
        self.__privkey = privkey
        self.__pubkey = pubkey

    def __generate_signed_ticket(self, ticket):
        signed_ticket = Signature(dictionary={
            "signature": pastel_id_write_signature_on_data_func(ticket.serialize(), self.__privkey, self.__pubkey),
            "pubkey": self.__pubkey,
        })

        # make sure we validate correctly
        signed_ticket.validate(ticket)
        return signed_ticket

    def __generate_final_ticket(self, cls, ticket, signature, mn_signatures):
        # create combined registration ticket
        final_ticket = cls(dictionary={
            "ticket": ticket.to_dict(),
            "signature_author": signature.to_dict(),
            "signature_1": mn_signatures[0].to_dict(),
            "signature_2": mn_signatures[1].to_dict(),
            "signature_3": mn_signatures[2].to_dict(),
            "nonce": str(uuid.uuid4()),
        })

        # make sure we validate correctly
        # FIXME: suppress validation on client. pyNodes should care about validation, but not wallet.
        # final_ticket.validate(self.__chainwrapper)
        return final_ticket

    async def __collect_mn_regticket_signatures(self, signature, ticket, masternode_ordering):
        signatures = []
        for mn in masternode_ordering:
            data_from_mn = await mn.call_masternode("SIGNREGTICKET_REQ", "SIGNREGTICKET_RESP",
                                                    [signature.serialize(), ticket.serialize()])

            # client parses signed ticket and validated signature
            mn_signature = Signature(serialized=data_from_mn)

            # is the data the same and the signature valid?
            if NetWorkSettings.VALIDATE_MN_SIGNATURES:
                require_true(mn_signature.pubkey == mn.pubkey)
            mn_signature.validate(ticket)

            # add signature to collected signatures
            signatures.append(mn_signature)
        return signatures

    async def __collect_mn_actticket_signatures(self, signature, ticket, image, masternode_ordering):
        # TODO: refactor the two MN signature collection functions into one
        signatures = []
        for mn in masternode_ordering:
            data_from_mn = await mn.call_masternode("SIGNACTTICKET_REQ", "SIGNACTTICKET_RESP", [signature.serialize(),
                                                                                                ticket.serialize(),
                                                                                                image.serialize()])

            # client parses signed ticket and validated signature
            mn_signature = Signature(serialized=data_from_mn)

            # is the data the same and the signature valid?
            if NetWorkSettings.VALIDATE_MN_SIGNATURES:
                require_true(mn_signature.pubkey == mn.pubkey)
            mn_signature.validate(ticket)

            # add signature to collected signatures
            signatures.append(mn_signature)
        return signatures

    def __rpc_mn_store_image(self, regticket_txid, image, mn):
        mn.masternode_place_image_data_in_chunkstorage(regticket_txid, image.serialize())

    def __wait_for_ticket_on_blockchain(self, regticket_txid):
        new_ticket = self.__chainwrapper.retrieve_ticket(regticket_txid)

        # validate new ticket
        new_ticket.validate(self.__chainwrapper)
        return new_ticket

    async def get_workers_fee(self, image_data, artist_name=None, artist_website=None, artist_written_statement=None,
                              artwork_title=None, artwork_series_name=None, artwork_creation_video_youtube_url=None,
                              artwork_keyword_set=None, total_copies=None):
        image = ImageData(dictionary={
            "image": image_data,
            "lubychunks": ImageData.generate_luby_chunks(image_data),
            "thumbnail": ImageData.generate_thumbnail(image_data),
        })

        image.validate()
        blocknum = self.__chainwrapper.get_last_block_number()
        regticket = RegistrationTicket(dictionary={
            "artist_name": artist_name,
            "artist_website": artist_website,
            "artist_written_statement": artist_written_statement,

            "artwork_title": artwork_title,
            "artwork_series_name": artwork_series_name,
            "artwork_creation_video_youtube_url": artwork_creation_video_youtube_url,
            "artwork_keyword_set": artwork_keyword_set,
            "total_copies": total_copies,

            "fingerprints": image.generate_fingerprints(),
            "lubyhashes": image.get_luby_hashes(),
            "lubyseeds": image.get_luby_seeds(),
            "thumbnailhash": image.get_thumbnail_hash(),

            "author": self.__pubkey,
            "order_block_txid": self.__chainwrapper.get_last_block_hash(),
            "blocknum": blocknum,
            "imagedata_hash": image.get_artwork_hash(),
        })
        regticket_signature = self.__generate_signed_ticket(regticket)
        regticket_db = RegticketDB.create(created=datetime.now(), blocknum=blocknum,
                                          serialized_regticket=regticket.serialize(),
                                          serialized_signature=regticket_signature.serialize())

        mn0, mn1, mn2 = self.__nodemanager.get_masternode_ordering()
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

        mn0, mn1, mn2 = self.__nodemanager.get_masternode_ordering(regticket_db.blocknum)

        async def send_regticket_to_mn(mn, serialized_regticket, serialized_signature, img_data):
            """
            Here we push ticket to given masternode, receive upload_code, then push image.
            Masternode will return fee, but we ignore it here.
            """
            upload_code = await mn.call_masternode("REGTICKET_REQ", "REGTICKET_RESP",
                                                   [serialized_regticket, serialized_signature])
            worker_fee = await mn.call_masternode("IMAGE_UPLOAD_REQ", "IMAGE_UPLOAD_RESP",
                                                  {'image_data': img_data, 'upload_code': upload_code})
            return upload_code

        upload_code_mn1, upload_code_mn2 = await asyncio.gather(
            send_regticket_to_mn(mn1, regticket_db.serialized_regticket, regticket_db.serialized_signature, image_data),
            send_regticket_to_mn(mn2, regticket_db.serialized_regticket, regticket_db.serialized_signature, image_data),
            return_exceptions=True
        )
        art_reg_client_logger.warn('Upload code1: {}'.format(upload_code_mn1))
        art_reg_client_logger.warn('Upload code2: {}'.format(upload_code_mn2))
        regticket_db.upload_code_mn1 = upload_code_mn1
        regticket_db.upload_code_mn2 = upload_code_mn2
        regticket_db.save()
        return 'OK'

    async def register_image(self, image_data, artist_name=None, artist_website=None, artist_written_statement=None,
                             artwork_title=None, artwork_series_name=None, artwork_creation_video_youtube_url=None,
                             artwork_keyword_set=None, total_copies=None):
        # generate image ticket
        image = ImageData(dictionary={
            "image": image_data,
            "lubychunks": ImageData.generate_luby_chunks(image_data),
            "thumbnail": ImageData.generate_thumbnail(image_data),
        })

        image.validate()

        # generate registration ticket
        regticket = RegistrationTicket(dictionary={
            "artist_name": artist_name,
            "artist_website": artist_website,
            "artist_written_statement": artist_written_statement,

            "artwork_title": artwork_title,
            "artwork_series_name": artwork_series_name,
            "artwork_creation_video_youtube_url": artwork_creation_video_youtube_url,
            "artwork_keyword_set": artwork_keyword_set,
            "total_copies": total_copies,

            "fingerprints": image.generate_fingerprints(),
            "lubyhashes": image.get_luby_hashes(),
            "lubyseeds": image.get_luby_seeds(),
            "thumbnailhash": image.get_thumbnail_hash(),

            "author": self.__pubkey,
            "order_block_txid": self.__chainwrapper.get_last_block_hash(),
            "blocknum": self.__chainwrapper.get_last_block_number(),
            "imagedata_hash": image.get_artwork_hash(),
        })

        # Current validation never passes - skip it for now.
        # Probably we should not validate any created tickets
        # Other nodes (ArtRegistrationServer) will validate, but client pushed ticket
        # to the network 'as is'.
        # regticket.validate(self.__chainwrapper)

        # get masternode ordering from regticket
        art_reg_client_logger.info('Get masternode ordering')
        masternode_ordering = self.__nodemanager.get_masternode_ordering(regticket.order_block_txid)
        art_reg_client_logger.info('Get masternode ordering ... done')
        mn0, mn1, mn2 = masternode_ordering

        # sign ticket
        # FIXME: No need to sign ticket here, cause every message sent to MN is signed in `pack_and_sign` method.
        # mn_ticket_logger.info('Sign ticket')
        signature_regticket = self.__generate_signed_ticket(regticket)
        # mn_ticket_logger.info('Sign ticket .... done')

        art_reg_client_logger.info('Initially sending regticket to the first masternode')
        upload_code = await mn0.call_masternode("REGTICKET_REQ", "REGTICKET_RESP",
                                                regticket.serialize())
        art_reg_client_logger.info('Upload code received: {}'.format(upload_code))

        # TODO: upload image to MN0 using upload code
        # TODO: (design upload_code logic/behaviour) - implement in MN code/art regisgration server
        # TODO: get final fee from MN0

        worker_fee = await mn0.call_masternode("IMAGE_UPLOAD_REQ", "IMAGE_UPLOAD_RESP",
                                               {'image_data': image_data, 'upload_code': upload_code})

        art_reg_client_logger.info('Worker fee received: {}'.format(worker_fee))

        # TODO: below is old code, which is being replaced with new one

        # have masternodes sign the ticket
        art_reg_client_logger.info('Collect signatures')
        mn_signatures = await self.__collect_mn_regticket_signatures(signature_regticket, regticket,
                                                                     masternode_ordering)
        art_reg_client_logger.info('Collect signatures ... done')
        # assemble final regticket
        final_regticket = self.__generate_final_ticket(FinalRegistrationTicket, regticket, signature_regticket,
                                                       mn_signatures)
        # ask first MN to store regticket on chain
        regticket_txid = await mn0.call_masternode("PLACEONBLOCKCHAIN_REQ", "PLACEONBLOCKCHAIN_RESP",
                                                   ["regticket", final_regticket.serialize()])

        # wait for regticket to show up on the chain
        self.__wait_for_ticket_on_blockchain(regticket_txid)

        # generate activation ticket
        actticket = ActivationTicket(dictionary={
            "author": self.__pubkey,
            "order_block_txid": regticket.order_block_txid,
            "registration_ticket_txid": regticket_txid,
        })
        actticket.validate(self.__chainwrapper, image)

        # sign actticket
        signature_actticket = self.__generate_signed_ticket(actticket)

        # place image in chunkstorage
        await mn0.call_masternode("PLACEINCHUNKSTORAGE_REQ", "PLACEINCHUNKSTORAGE_RESP",
                                  [regticket_txid, image.serialize()])

        # have masternodes sign the ticket
        mn_signatures = await self.__collect_mn_actticket_signatures(signature_actticket, actticket, image,
                                                                     masternode_ordering)

        # create combined activation ticket
        final_actticket = self.__generate_final_ticket(FinalActivationTicket, actticket, signature_actticket,
                                                       mn_signatures)

        # ask first MN to store regticket on chain
        actticket_txid = await mn0.call_masternode("PLACEONBLOCKCHAIN_REQ", "PLACEONBLOCKCHAIN_RESP",
                                                   ["actticket", final_actticket.serialize()])

        return actticket_txid
