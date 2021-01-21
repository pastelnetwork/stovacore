import asyncio
import json
import uuid
from decimal import Decimal

import time

from datetime import datetime

from peewee import DoesNotExist

from core_modules.blackbox_modules.nsfw import get_nsfw_detector
from core_modules.chunkmanager import get_chunkmanager
from core_modules.database import Regticket, MASTERNODE_DB, Chunk
from utils.mn_ordering import get_masternode_ordering
from cnode_connection import get_blockchain_connection
from .ticket_models import RegistrationTicket, Signature, ImageData

from core_modules.helpers import require_true, bytes_to_chunkid
from core_modules.logger import initlogging

mn_ticket_logger = initlogging('Ticket Manager', __name__)


async def is_burn_10_tx_height_valid(regticket, txid):
    regticket = RegistrationTicket(serialized=regticket.regticket)
    sleep_counter = 0
    while True:
        try:
            raw_tx_data = get_blockchain_connection().getrawtransaction(txid, verbose=1)
            break
        except Exception as ex:
            await asyncio.sleep(5)
            if sleep_counter > 10:
                raise ex

    if not raw_tx_data:
        return False, 'Burn 10% txid is invalid'

    if raw_tx_data['expiryheight'] < regticket.blocknum:
        return False, 'Fee transaction is older then regticket.'
    return True, None


async def is_burn_10_tx_amount_valid(regticket, txid):
    networkfee_result = get_blockchain_connection().getnetworkfee()
    networkfee = networkfee_result['networkfee']
    tx_amounts = []
    sleep_counter = 0
    while True:
        try:
            raw_tx_data = get_blockchain_connection().getrawtransaction(txid, verbose=1)
            break
        except Exception as ex:
            await asyncio.sleep(5)
            if sleep_counter > 10:
                raise ex

    for vout in raw_tx_data['vout']:
        tx_amounts.append(vout['value'])

    if regticket.localfee is not None:
        # we're main masternode (MN0)
        valid = False
        for tx_amount in tx_amounts:
            if regticket.localfee * Decimal(
                    '0.099') <= tx_amount <= regticket.localfee * Decimal('0.101'):
                valid = True
                break
        if not valid:
            return False, 'Wrong fee amount'
        regticket.is_valid_mn0 = True
        regticket.save()
        return True, None
    else:
        # we're MN1 or MN2
        # we don't know exact MN0 fee, but it should be almost equal to the networkfee
        valid = False
        for tx_amount in tx_amounts:
            if networkfee * 0.09 <= tx_amount <= networkfee * 0.11:
                valid = True
                break
        if not valid:
            return False, 'Payment amount differs with 10% of fee size.'
        else:
            return True, None


async def is_burn_tx_valid(regticket, txid):
    is_valid_height, height_err = await is_burn_10_tx_height_valid(regticket, txid)
    is_valid_amount, amount_err = await is_burn_10_tx_amount_valid(regticket, txid)
    if is_valid_height and is_valid_amount:
        return True, None
    else:
        regticket.delete()
        return False, (height_err, amount_err)


def masternode_place_image_data_in_chunkstorage(regticket, regticket_image_data):
    """
    Place image to the chunkstorage. Initially artwork is placed to the so called temporary storage
    (which exist only on the given masternode and is not distributed to other).
    After activation ticket will be created (by the wallet) and parsed by current masternode  -
    masternode will move artwork chunks to regular chunkstorage and start promote chunks to
    other masternodes, so artwork will be stored distributedly.
    """
    # reconstruct image with seeds from regticket.
    # then and only then chunk set will be identical to what wallet generated (and which hashes
    # are written to the regticket.lubyhashes).
    imagedata = ImageData(dictionary={
        "image": regticket_image_data,
        "lubychunks": ImageData.generate_luby_chunks(regticket_image_data, seeds=regticket.lubyseeds),
        "thumbnail": ImageData.generate_thumbnail(regticket_image_data),
    })
    artwork_hash = imagedata.get_artwork_hash()
    # store thumbnail
    get_chunkmanager().store_chunk_in_temp_storage(bytes_to_chunkid(regticket.thumbnailhash), imagedata.thumbnail)
    Chunk.create_from_hash(chunkhash=regticket.thumbnailhash, artwork_hash=regticket.thumbnailhash, stored=True)

    # store chunks
    for chunkhash, chunkdata in zip(imagedata.get_luby_hashes(), imagedata.lubychunks):
        chunkhash_int = bytes_to_chunkid(chunkhash)
        get_chunkmanager().store_chunk_in_temp_storage(chunkhash_int, chunkdata)
        mn_ticket_logger.debug('Adding chunk id to DB: {}'.format(chunkhash_int))
        # keep track of chunks in the local SQLite database.
        # we should be ably to find all chunks by artwork hash as well.

        # save chunk in database and mark `Stored` = True as we've already stored it in the storage (at least temp).
        Chunk.create_from_hash(chunkhash=chunkhash, artwork_hash=artwork_hash, stored=True)


class ArtRegistrationServer:
    def __init__(self):
        self.__chunkmanager = get_chunkmanager()
        mn_ticket_logger.debug("Art Registration Server initialized")

    def __generate_signed_ticket(self, ticket):

        # we sign cnode_container of Regticket. as anything passed to `pastelid_sign` is converted to base64
        # we just send bytes(json(cnode_container)) there.

        signature = get_blockchain_connection().pastelid_sign(ticket.serialize_base64())
        signed_ticket = Signature(dictionary={
            "signature": signature,
            "pastelid": get_blockchain_connection().pastelid,
        })

        # make sure we validate correctly
        signed_ticket.validate(ticket)
        return signed_ticket

    @property
    def rpc_handler_list(self):
        return [("REGTICKET_REQ", "REGTICKET_RESP",
                 self.masternode_validate_registration_ticket),
                ("IMAGE_UPLOAD_MN0_REQ", "IMAGE_UPLOAD_MN0_RESP",
                 self.masternode_image_upload_request_mn0),
                ("IMAGE_UPLOAD_REQ", "IMAGE_UPLOAD_RESP",
                 self.masternode_image_upload_request),
                ("TXID_10_REQ", "TXID_10_RESP",
                 self.masternode_validate_txid_upload_code_image,
                 True),
                ("REGTICKET_MN1_CONFIRM_REQ", "REGTICKET_MN1_CONFIRM_RESP",
                 self.masternode_mn1_confirm),
                ("REGTICKET_STATUS_REQ", "REGTICKET_STATUS_RESP",
                 self.regticket_status),
                ]

    def masternode_sign_registration_ticket(self, data, *args, **kwargs):
        # parse inputs
        signature_serialized, regticket_serialized = data
        signed_regticket = Signature(serialized=signature_serialized)
        regticket = RegistrationTicket(serialized=regticket_serialized)

        # validate client's signature on the ticket
        require_true(signed_regticket.pastelid == regticket.author)
        signed_regticket.validate(regticket)

        # validate registration ticket
        regticket.validate()

        # sign regticket
        signature = get_blockchain_connection().pastelid_sign(regticket.serialize_base64())
        ticket_signed_by_mn = Signature(dictionary={
            "signature": signature,
            "pastelid": get_blockchain_connection().pastelid,
        })
        return ticket_signed_by_mn.serialize()

    def masternode_validate_registration_ticket(self, data, *args, **kwargs):
        # parse inputs
        artist_pk = kwargs.get('sender_id')
        mn_ticket_logger.info('Masternode validate regticket, data: {}'.format(data))
        regticket_serialized, regticket_signature_serialized = data
        regticket = RegistrationTicket(serialized=regticket_serialized)
        signed_regticket = Signature(serialized=regticket_signature_serialized)
        require_true(signed_regticket.pastelid == regticket.author)
        signed_regticket.validate(regticket)

        # validate registration ticket
        regticket.validate()
        upload_code = uuid.uuid4().bytes

        # TODO: clean upload code and regticket from local db when ticket was placed on the blockchain
        # TODO: clean upload code and regticket from local db if they're old enough
        MASTERNODE_DB.connect(reuse_if_open=True)
        Regticket.create(regticket=regticket_serialized, upload_code=upload_code, created=datetime.now(),
                         artists_signature_ticket=regticket_signature_serialized, artist_pk=artist_pk,
                         image_hash=regticket.imagedata_hash)
        return upload_code

    def masternode_image_upload_request(self, data, *args, **kwargs):
        # parse inputs
        upload_code = data['upload_code']
        image_data = data['image_data']
        mn_ticket_logger.info('Masternode image upload received, upload_code: {}'.format(upload_code))
        sender_id = kwargs.get('sender_id')
        MASTERNODE_DB.connect(reuse_if_open=True)
        try:
            regticket_db = Regticket.get(upload_code=upload_code)
            regticket = RegistrationTicket(serialized=regticket_db.regticket)
            if regticket.author != sender_id:
                raise Exception('Given upload code was created by other public key')
            mn_ticket_logger.info('Given upload code exists with required public key')
        except DoesNotExist:
            mn_ticket_logger.exception('Given upload code DOES NOT exists with required public key')
            raise
        regticket_db.image_data = image_data
        regticket_db.save()

    def masternode_image_upload_request_mn0(self, data, *args, **kwargs):
        # parse inputs
        upload_code = data['upload_code']
        image_data = data['image_data']
        mn_ticket_logger.info('Masternode image upload received, upload_code: {}'.format(upload_code))
        sender_id = kwargs.get('sender_id')
        MASTERNODE_DB.connect(reuse_if_open=True)
        try:
            regticket_db = Regticket.get(upload_code=upload_code)
            regticket = RegistrationTicket(serialized=regticket_db.regticket)
            if regticket.author != sender_id:
                raise Exception('Given upload code was created by other public key')
            mn_ticket_logger.info('Given upload code exists with required public key')
        except DoesNotExist:
            mn_ticket_logger.exception('Given upload code DOES NOT exists with required public key')
            raise
        result = get_blockchain_connection().getlocalfee()
        fee = result['localfee']
        regticket_db.image_data = image_data
        regticket_db.localfee = fee
        regticket_db.save()
        return fee

    def regticket_status(self, data, *args, **kwargs):
        # verify identity - return status only to regticket creator
        sender_id = kwargs.get('sender_id')
        upload_code = data.get('upload_code')
        MASTERNODE_DB.connect(reuse_if_open=True)
        try:
            regticket_db = Regticket.get(artist_pk=sender_id, upload_code=upload_code)
        except DoesNotExist:
            raise Exception('Given upload code DOES NOT exists with required public key')
        return {'status': regticket_db.status, 'error': regticket_db.error}

    def masternode_mn1_confirm(self, data, *args, **kwargs):
        # parse inputs
        artist_pk, image_hash, serialized_signature = data
        sender_id = kwargs.get('sender_id')
        MASTERNODE_DB.connect(reuse_if_open=True)
        mn_ticket_logger.info('masternode_mn1_confirm: received confirmation from {}'.format(sender_id))

        regticket_db_set = Regticket.select().where(Regticket.artist_pk == artist_pk,
                                                    Regticket.image_hash == image_hash)
        if len(regticket_db_set) == 0:
            raise Exception('Regticket not found for given artist ID and image hash')

        if len(regticket_db_set) > 2:
            regticket_db = regticket_db_set[-1]
            Regticket.delete().where(Regticket.id < regticket_db.id)
        else:
            regticket_db = regticket_db_set[0]

        if regticket_db.is_valid_mn1 is None:
            # first confirmation has came
            regticket_db.is_valid_mn1 = True
            regticket_db.mn1_pk = sender_id
            regticket_db.mn1_serialized_signature = serialized_signature
            regticket_db.save()
        else:
            if regticket_db.is_valid_mn2 is None:
                if regticket_db.mn1_pk == sender_id:
                    raise Exception('I already have confirmation from this masternode')
                # second confirmation has came
                regticket_db.is_valid_mn2 = True
                regticket_db.mn2_pk = sender_id
                regticket_db.mn2_serialized_signature = serialized_signature
                regticket_db.save()
                regticket = RegistrationTicket(serialized=regticket_db.regticket)
                # store image and thumbnail in chunkstorage
                masternode_place_image_data_in_chunkstorage(regticket, regticket_db.image_data)

                txid = regticket_db.write_to_blockchain()
                return txid
            else:
                raise Exception('All 2 confirmations received for a given ticket')
        mn_ticket_logger.info('Confirmation from MN received')
        return 'Validation passed'

    async def masternode_validate_txid_upload_code_image(self, data, *args, **kwargs):
        burn_10_txid, upload_code = data
        try:
            regticket_db = Regticket.get(upload_code=upload_code)
        except DoesNotExist:
            mn_ticket_logger.exception('Upload code {} not found in DB'.format(upload_code))
            raise ValueError('Given upload code was issued by someone else...')
        is_valid, errors = await is_burn_tx_valid(regticket_db, burn_10_txid)
        if not is_valid:
            raise ValueError(errors)
        regticket = RegistrationTicket(serialized=regticket_db.regticket)
        # TODO: perform duplication check
        if get_nsfw_detector().is_nsfw(regticket_db.image_data):
            raise ValueError("Image is NSFW, score: %s" % get_nsfw_detector().get_score(regticket_db.image_data))

        # if we're on mn1 or mn2:
        if regticket_db.localfee is None:
            mn0 = get_masternode_ordering(regticket.blocknum)[0]
            # Send confirmation to MN0
            mn_signed_regticket = self.__generate_signed_ticket(regticket)
            # TODO: run task and return without waiting for result (as if it was in Celery)
            # TODO: handle errors/exceptions
            response = await mn0.call_masternode("REGTICKET_MN1_CONFIRM_REQ",
                                                 "REGTICKET_MN1_CONFIRM_RESP",
                                                 [regticket.author, regticket.imagedata_hash,
                                                  mn_signed_regticket.serialize()])
            # We return success status cause validation on this node has passed. However exception may happen when
            # calling mn0 - need to handle it somehow (or better - schedule async task).
            return response
        else:
            return 'Validation passed'
