import uuid
import time

from .ticket_models import RegistrationTicket, Signature, FinalRegistrationTicket, ActivationTicket,\
    FinalActivationTicket, ImageData, IDTicket, FinalIDTicket, TransferTicket, FinalTransferTicket, TradeTicket,\
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
        rpcserver.add_callback("SIGNREGTICKET_REQ", "SIGNREGTICKET_RESP",
                               self.masternode_sign_registration_ticket)
        rpcserver.add_callback("SIGNACTTICKET_REQ", "SIGNACTTICKET_RESP",
                               self.masternode_sign_activation_ticket)
        rpcserver.add_callback("PLACEONBLOCKCHAIN_REQ", "PLACEONBLOCKCHAIN_RESP",
                               self.masternode_place_ticket_on_blockchain)
        rpcserver.add_callback("PLACEINCHUNKSTORAGE_REQ", "PLACEINCHUNKSTORAGE_RESP",
                               self.masternode_place_image_data_in_chunkstorage)

    def masternode_sign_registration_ticket(self, data):
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

    def masternode_sign_activation_ticket(self, data):
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

    def masternode_place_ticket_on_blockchain(self, data):
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

    def masternode_place_image_data_in_chunkstorage(self, data):
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
        final_ticket.validate(self.__chainwrapper)
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
            "imagedata_hash": image.get_artwork_hash(),
        })

        # Current validation never passes - skip it for now.
        # Probably we should not validate any created tickets
        # Other nodes (ArtRegistrationServer) will validate, but client pushed ticket
        # to the network 'as is'.
        # regticket.validate(self.__chainwrapper)

        # get masternode ordering from regticket
        masternode_ordering = self.__nodemanager.get_masternode_ordering(regticket.order_block_txid)
        mn0, mn1, mn2 = masternode_ordering

        # sign ticket
        signature_regticket = self.__generate_signed_ticket(regticket)

        # have masternodes sign the ticket
        mn_signatures = await self.__collect_mn_regticket_signatures(signature_regticket, regticket, masternode_ordering)

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
        await mn0.call_masternode("PLACEINCHUNKSTORAGE_REQ", "PLACEINCHUNKSTORAGE_RESP", [regticket_txid, image.serialize()])

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
            "signature": pastel_id_write_signature_on_data_func(transferticket.serialize(), self.__privkey, self.__pubkey),
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
