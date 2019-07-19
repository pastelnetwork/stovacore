import uuid
import time

from datetime import datetime

from peewee import DoesNotExist

from core_modules.database import UploadCode, db
from .ticket_models import RegistrationTicket, Signature, FinalRegistrationTicket, ActivationTicket, \
    FinalActivationTicket, ImageData, IDTicket, FinalIDTicket, TransferTicket, FinalTransferTicket, TradeTicket, \
    FinalTradeTicket
from PastelCommon.signatures import pastel_id_write_signature_on_data_func
from core_modules.settings import NetWorkSettings
from core_modules.helpers import require_true, bytes_to_chunkid
from core_modules.jailed_image_parser import JailedImageParser
from core_modules.logger import initlogging

mn_ticket_logger = initlogging('Logger', __name__)


class ArtRegistrationServer:
    def __init__(self, nodenum, privkey, pubkey, chainwrapper, chunkmanager):
        self.__nodenum = nodenum
        self.__priv = privkey
        self.__pub = pubkey
        self.__chainwrapper = chainwrapper
        self.__chunkmanager = chunkmanager

        # this is to aid testing
        self.pubkey = self.__pub

    def register_rpcs(self, rpcserver):
        rpcserver.add_callback("REGTICKET_REQ", "REGTICKET_RESP",
                               self.masternode_validate_registration_ticket)
        rpcserver.add_callback("IMAGE_UPLOAD_REQ", "IMAGE_UPLOAD_RESP",
                               self.masternode_image_upload_request)
        rpcserver.add_callback("SIGNREGTICKET_REQ", "SIGNREGTICKET_RESP",
                               self.masternode_sign_registration_ticket)
        rpcserver.add_callback("SIGNACTTICKET_REQ", "SIGNACTTICKET_RESP",
                               self.masternode_sign_activation_ticket)
        rpcserver.add_callback("PLACEONBLOCKCHAIN_REQ", "PLACEONBLOCKCHAIN_RESP",
                               self.masternode_place_ticket_on_blockchain)
        rpcserver.add_callback("PLACEINCHUNKSTORAGE_REQ", "PLACEINCHUNKSTORAGE_RESP",
                               self.masternode_place_image_data_in_chunkstorage)

    def masternode_sign_registration_ticket(self, data, *args, **kwargs):
        # parse inputs
        signature_serialized, regticket_serialized = data
        signed_regticket = Signature(serialized=signature_serialized)
        regticket = RegistrationTicket(serialized=regticket_serialized)

        # validate client's signature on the ticket
        require_true(signed_regticket.pubkey == regticket.author)
        signed_regticket.validate(regticket)

        # validate registration ticket
        regticket.validate(self.__chainwrapper)

        # sign regticket
        ticket_signed_by_mn = Signature(dictionary={
            "signature": pastel_id_write_signature_on_data_func(regticket_serialized, self.__priv, self.__pub),
            "pubkey": self.__pub,
        })
        return ticket_signed_by_mn.serialize()

    def masternode_validate_registration_ticket(self, data, *args, **kwargs):
        # parse inputs
        regticket_serialized = data
        mn_ticket_logger.info('Masternode validate regticket, data: {}'.format(data))
        regticket = RegistrationTicket(serialized=regticket_serialized)

        # validate registration ticket
        regticket.validate(self.__chainwrapper)
        upload_code = uuid.uuid4().bytes

        # TODO: clean upload code and regticket from local db when ticket was placed on the blockchain
        # TODO: clean upload code and regticket from local db if they're old enough
        db.connect(reuse_if_open=True)
        UploadCode.create(regticket=regticket_serialized, upload_code=upload_code, created=datetime.now())

        return upload_code

    def validate_image(self, image_data):
        # TODO: we should validate image only after 10% burn fee is payed by the wallet
        # validate image
        image.validate()

        # get registration ticket
        final_regticket = chainwrapper.retrieve_ticket(self.registration_ticket_txid)

        # validate final ticket
        final_regticket.validate(chainwrapper)

        # validate registration ticket
        regticket = final_regticket.ticket

        # validate that the authors match
        require_true(regticket.author == self.author)

        # validate that imagehash, fingerprints, lubyhashes and thumbnailhash indeed belong to the image
        require_true(regticket.fingerprints == image.generate_fingerprints())  # TODO: is this deterministic?
        require_true(regticket.lubyhashes == image.get_luby_hashes())
        require_true(regticket.lubyseeds == image.get_luby_seeds())
        require_true(regticket.thumbnailhash == image.get_thumbnail_hash())

        # validate that MN order matches between registration ticket and activation ticket
        require_true(regticket.order_block_txid == self.order_block_txid)

        # image hash matches regticket hash
        require_true(regticket.imagedata_hash == image.get_artwork_hash())

        # run nsfw check
        if NSFWDetector.is_nsfw(image.image):
            raise ValueError("Image is NSFW, score: %s" % NSFWDetector.get_score(image.image))

    def masternode_image_upload_request(self, data, *args, **kwargs):
        # parse inputs
        upload_code = data['upload_code']
        image_data = data['image_data']
        mn_ticket_logger.info('Masternode image upload received, upload_code: {}'.format(upload_code))
        sender_id = kwargs.get('sender_id')
        db.connect(reuse_if_open=True)
        try:
            upload_code_db_record = UploadCode.get(upload_code=upload_code)
            regticket = RegistrationTicket(serialized=upload_code_db_record.regticket)
            if regticket.author != sender_id:
                raise Exception('Given upload code was created by other public key')
            mn_ticket_logger.info('Given upload code exists with required public key')
        except DoesNotExist:
            mn_ticket_logger.warn('Given upload code DOES NOT exists with required public key')
            raise
        upload_code_db_record.image_data = image_data
        upload_code_db_record.save()
        fee = 0.01*(len(image_data)/1024)  # PSL # TODO: calculate fee
        return fee

    def masternode_sign_activation_ticket(self, data, *args, **kwargs):
        # parse inputs
        signature_serialized, activationticket_serialized, image_serialized = data
        signed_actticket = Signature(serialized=signature_serialized)
        image = ImageData(serialized=image_serialized)
        activation_ticket = ActivationTicket(serialized=activationticket_serialized)

        # test image data for validity in a jailed environment
        converter = JailedImageParser(self.__nodenum, image.image)
        converter.parse()

        # validate client's signature on the ticket - so only original client can activate
        require_true(signed_actticket.pubkey == activation_ticket.author)
        signed_actticket.validate(activation_ticket)

        # validate activation ticket
        activation_ticket.validate(self.__chainwrapper, image)

        # sign activation ticket
        ticket_signed_by_mn = Signature(dictionary={
            "signature": pastel_id_write_signature_on_data_func(activationticket_serialized, self.__priv, self.__pub),
            "pubkey": self.__pub,
        })
        return ticket_signed_by_mn.serialize()

    def masternode_place_ticket_on_blockchain(self, data, *args, **kwargs):
        tickettype, ticket_serialized = data
        if tickettype == "regticket":
            ticket = FinalRegistrationTicket(serialized=ticket_serialized)
        elif tickettype == "actticket":
            ticket = FinalActivationTicket(serialized=ticket_serialized)
        else:
            raise TypeError("Invalid ticket type: %s" % tickettype)

        # validate signed ticket
        ticket.validate(self.__chainwrapper)

        # place ticket on the blockchain
        return self.__chainwrapper.store_ticket(ticket)

    def masternode_place_image_data_in_chunkstorage(self, data, *args, **kwargs):
        regticket_txid, imagedata_serialized = data

        imagedata = ImageData(serialized=imagedata_serialized)
        image_hash = imagedata.get_thumbnail_hash()

        # verify that this is an actual image that is being registered
        final_regticket = self.__chainwrapper.retrieve_ticket(regticket_txid)
        final_regticket.validate(self.__chainwrapper)

        # store thumbnail
        self.__chunkmanager.store_chunk_in_temp_storage(bytes_to_chunkid(image_hash), imagedata.thumbnail)

        # store chunks
        for chunkhash, chunkdata in zip(imagedata.get_luby_hashes(), imagedata.lubychunks):
            chunkhash_int = bytes_to_chunkid(chunkhash)
            self.__chunkmanager.store_chunk_in_temp_storage(chunkhash_int, chunkdata)



class IDRegistrationClient:
    def __init__(self, privkey, pubkey, chainwrapper):
        self.__privkey = privkey
        self.__pubkey = pubkey
        self.__chainwrapper = chainwrapper

    def register_id(self, address):
        idticket = IDTicket(dictionary={
            "blockchain_address": address,
            "public_key": self.__pubkey,
            "ticket_submission_time": int(time.time()),
        })
        idticket.validate()

        signature = Signature(dictionary={
            "signature": pastel_id_write_signature_on_data_func(idticket.serialize(), self.__privkey, self.__pubkey),
            "pubkey": self.__pubkey,
        })
        signature.validate(idticket)

        finalticket = FinalIDTicket(dictionary={
            "ticket": idticket.to_dict(),
            "signature": signature.to_dict(),
            "nonce": str(uuid.uuid4()),
        })
        finalticket.validate(self.__chainwrapper)

        self.__chainwrapper.store_ticket(finalticket)


class TransferRegistrationClient:
    def __init__(self, privkey, pubkey, chainwrapper, artregistry):
        self.__privkey = privkey
        self.__pubkey = pubkey
        self.__chainwrapper = chainwrapper
        self.__artregistry = artregistry

    def register_transfer(self, recipient_pubkey, imagedata_hash, copies):
        transferticket = TransferTicket(dictionary={
            "public_key": self.__pubkey,
            "recipient": recipient_pubkey,
            "imagedata_hash": imagedata_hash,
            "copies": copies,
        })
        transferticket.validate(self.__chainwrapper, self.__artregistry)

        # Make sure enough remaining copies are left on our key
        # We do this here to prevent creating a ticket we know now as invalid. However anything
        # might happen before this tickets makes it to the network, os this check can't be put in validate()
        require_true(self.__artregistry.enough_copies_left(transferticket.imagedata_hash,
                                                           transferticket.public_key,
                                                           transferticket.copies))

        signature = Signature(dictionary={
            "signature": pastel_id_write_signature_on_data_func(transferticket.serialize(), self.__privkey,
                                                                self.__pubkey),
            "pubkey": self.__pubkey,
        })
        signature.validate(transferticket)

        finalticket = FinalTransferTicket(dictionary={
            "ticket": transferticket.to_dict(),
            "signature": signature.to_dict(),
            "nonce": str(uuid.uuid4()),
        })
        finalticket.validate(self.__chainwrapper)

        self.__chainwrapper.store_ticket(finalticket)


class TradeRegistrationClient:
    def __init__(self, privkey, pubkey, blockchain, chainwrapper, artregistry):
        self.__privkey = privkey
        self.__pubkey = pubkey
        self.__blockchain = blockchain
        self.__chainwrapper = chainwrapper
        self.__artregistry = artregistry

    async def register_trade(self, imagedata_hash, tradetype, watched_address, copies, price, expiration):
        # move funds to new address
        if tradetype == "bid":
            collateral_txid = await self.__chainwrapper.move_funds_to_new_wallet(self.__pubkey, watched_address,
                                                                                 copies, price)
        else:
            # this is unused in ask tickets
            collateral_txid = "0000000000000000000000000000000000000000000000000000000000000000"

        tradeticket = TradeTicket(dictionary={
            "public_key": self.__pubkey,
            "imagedata_hash": imagedata_hash,
            "type": tradetype,
            "copies": copies,
            "price": price,
            "expiration": expiration,
            "watched_address": watched_address,
            "collateral_txid": collateral_txid,
        })
        tradeticket.validate(self.__blockchain, self.__chainwrapper, self.__artregistry)

        signature = Signature(dictionary={
            "signature": pastel_id_write_signature_on_data_func(tradeticket.serialize(), self.__privkey, self.__pubkey),
            "pubkey": self.__pubkey,
        })
        signature.validate(tradeticket)

        finalticket = FinalTradeTicket(dictionary={
            "ticket": tradeticket.to_dict(),
            "signature": signature.to_dict(),
            "nonce": str(uuid.uuid4()),
        })
        finalticket.validate(self.__chainwrapper)

        self.__chainwrapper.store_ticket(finalticket)
