import base64
import io
import msgpack

from PIL import Image

from core_modules.helpers import get_pynode_digest_bytes, require_true
from PastelCommon.signatures import pastel_id_verify_signature_with_public_key_func
from core_modules.logger import initlogging
from core_modules.model_validators import FieldValidator, StringField, IntegerField, FingerprintField, SHA3512Field, \
    LubyChunkHashField, LubyChunkField, ImageField, ThumbnailField, TXIDField, UUIDField, SignatureField, PubkeyField, \
    LubySeedField, BlockChainAddressField, UnixTimeField, StringChoiceField
from PastelCommon.dupe_detection import DupeDetector
from core_modules.blackbox_modules.dupe_detection_utils import measure_similarity, assemble_fingerprints_for_pandas
from core_modules.settings import NetWorkSettings

if not NetWorkSettings.FROZEN:
    from core_modules.blackbox_modules.nsfw import NSFWDetector

from core_modules.blackbox_modules import luby

ticket_logger = initlogging('Ticket logger', __name__)


# ===== VALIDATORS ===== #
class NotImplementedValidator:
    msg = "You forgot to set \"validators\" while inheriting from ModelBase!"

    def __index__(self):
        raise NotImplementedError(self.msg)

    def __getattr__(self, item):
        raise NotImplementedError(self.msg)

    def __call__(self, *args, **kwargs):
        raise NotImplementedError(self.msg)


class NotImplementedMethods:
    msg = "Your forgot to set \"methods\" while inheriting from ContainerModelBase!"

    def keys(self):
        raise NotImplementedError(self.msg)

    def items(self, item):
        raise NotImplementedError(self.msg)


class TicketModelBase:
    methods = NotImplementedMethods()
    """
        This class supports two constructors:
          o dictonary if you want to pass in the dictionary for the models directly, or
          o serialized if you want to pass in msgpack()ed data from the wire
        """

    def __init__(self, dictionary=None, serialized=None):
        # internal data structures
        # TODO: using __dict__ like this is not very elegant
        self.__dict__["__locked"] = False
        self.__data = {}
        # end

        if dictionary is None and serialized is None:
            raise ValueError("You have to set at least dictionary or serialized")

        if serialized is not None:
            unserialized = self.unserialize(serialized)
            dictionary = unserialized

        # validate dictionary
        if type(dictionary) != dict:
            raise TypeError("data should be a dict!")

        # validate all keys in data
        a, b = set(dictionary.keys()), set(self.methods.keys())
        if len(a - b) + len(b - a) > 0:
            raise KeyError("Keys don't match %s != %s" % (a, b))

        for name, validator in self.methods.items():
            value = dictionary[name]
            setattr(self, name, value)

        # lock setattr
        self.__dict__["__locked"] = True

    def __is_field_validator(self, validator):
        validator_type = type(validator)
        if issubclass(validator_type, FieldValidator):
            return True
        elif validator_type == type and issubclass(validator, TicketModelBase):
            return False
        else:
            raise TypeError("Invalid validator! type: %s, validator: %s" % (validator_type, validator))

    def __getattr__(self, key):
        # TODO: refactor getattr and setattr and use self.__class__.methods for
        # validation and not the lock. We don't really need the class to be immutable,
        # we are just trying to prevent the mistake of setting a data member accidentally and
        # thus circumventing validation.
        locked = self.__dict__["__locked"]
        if locked:
            return self.__data[key]
        else:
            return self.__dict__[key]

    def __setattr__(self, key, value):
        locked = self.__dict__["__locked"]
        if locked:
            raise NameError("Tried to set key %s, which is forbidden (use constructor)!" % key)

        if key.startswith("_"):
            self.__dict__[key] = value
        else:
            validator = self.__class__.methods[key]
            if self.__is_field_validator(validator):
                validated = validator.validate(value)
            else:
                validated = validator(dictionary=value)

            self.__data[key] = validated

    def __eq__(self, other):
        return self.__data == other

    def to_dict(self):
        ret = {}
        keys = sorted(self.__data.keys())
        for k in keys:
            v = self.__data[k]

            validator = self.__class__.methods[k]
            if self.__is_field_validator(validator):
                ret[k] = v
            else:
                ret[k] = v.to_dict()
        return ret

    def serialize(self):
        return msgpack.packb(self.to_dict(), use_bin_type=True)

    def unserialize(self, packed):
        return msgpack.unpackb(packed, raw=False)

    def get_hash(self):
        return get_pynode_digest_bytes(self.serialize())

    def validate(self, *args, **kwargs):
        raise NotImplementedError()


# ===== END ===== #


# ===== START NEW STYLE MODELS ===== #
class ImageData(TicketModelBase):
    methods = {
        "image": ImageField(),
        "lubychunks": LubyChunkField(),
        "thumbnail": ThumbnailField(),
    }

    def get_artwork_hash(self):
        return get_pynode_digest_bytes(self.image)

    def generate_fingerprints(self):
        fingerprints = DupeDetector(NetWorkSettings.DUPE_DETECTION_MODELS,
                                    NetWorkSettings.DUPE_DETECTION_TARGET_SIZE).compute_deep_learning_features(
            self.image)
        return fingerprints

    @staticmethod
    def generate_luby_chunks(imagedata):
        chunks = luby.encode(NetWorkSettings.LUBY_REDUNDANCY_FACTOR, NetWorkSettings.CHUNKSIZE, imagedata)

        # test that the chunks are correct
        luby.verify_blocks(chunks)

        return chunks

    @staticmethod
    def generate_thumbnail(imagedata):
        imagefile = io.BytesIO(imagedata)
        image = Image.open(imagefile)
        image.thumbnail(NetWorkSettings.THUMBNAIL_DIMENSIONS)

        with io.BytesIO() as output:
            # we use optimize=False to generate the same output every time
            image.save(output, "PNG", optimize=False, compress_level=9)
            contents = output.getvalue()
        return contents

    def get_luby_seeds(self):
        return luby.get_seeds(self.lubychunks)

    def get_luby_hashes(self):
        hashes = []
        for chunk in self.lubychunks:
            hashes.append(get_pynode_digest_bytes(chunk))
        return hashes

    def get_thumbnail_hash(self):
        return get_pynode_digest_bytes(self.thumbnail)

    def validate(self):
        # verify luby chunks

        luby.verify_blocks(self.lubychunks)

        # assemble image from chunks and check if it matches
        reconstructed = luby.decode(self.lubychunks)
        require_true(reconstructed == self.image)

        # validate that thumbnail is the same image
        # TODO: we should not regenerate the thumbnail, just look for similarities as this might not be deterministic
        new_thumbnail = self.generate_thumbnail(self.image)
        require_true(self.thumbnail == new_thumbnail)


class RegistrationTicket(TicketModelBase):
    methods = {
        # mandatory fields for Final Ticket
        "author": PubkeyField(),
        "order_block_txid": TXIDField(),
        "blocknum": IntegerField(minsize=0, maxsize=9999999999999),
        "imagedata_hash": SHA3512Field(),

        "artist_name": StringField(minsize=0, maxsize=120),
        "artist_website": StringField(minsize=0, maxsize=120),
        "artist_written_statement": StringField(minsize=0, maxsize=120),
        "artwork_title": StringField(minsize=0, maxsize=120),
        "artwork_series_name": StringField(minsize=0, maxsize=120),
        "artwork_creation_video_youtube_url": StringField(minsize=0, maxsize=120),
        "artwork_keyword_set": StringField(minsize=0, maxsize=120),
        "total_copies": IntegerField(minsize=0, maxsize=120),

        "fingerprints": FingerprintField(),
        "lubyhashes": LubyChunkHashField(),
        "lubyseeds": LubySeedField(),
        "thumbnailhash": SHA3512Field(),
    }

    def validate(self, chainwrapper):
        # we have no way to check these but will do so on activation:
        #  o fingerprints
        #  o lubyhashes
        #  o thumbnailhash
        #
        # after these checks are done we know that fingerprints are not dupes and there is no race

        # validate that lubyhashes and lubychunks are the same length
        require_true(len(self.lubyhashes) == len(self.lubyseeds))

        # validate that order txid is not too old
        block_distance = chainwrapper.get_block_distance(chainwrapper.get_last_block_hash(), self.order_block_txid)
        if block_distance > NetWorkSettings.MAX_REGISTRATION_BLOCK_DISTANCE:
            raise ValueError("Block distance between order_block_height and current block is too large!")
        # validate that art hash doesn't exist:
        # TODO: move this artwork index logic into chainwrapper
        fingerprint_db = {}
        for txid, ticket in chainwrapper.all_ticket_iterator():
            if type(ticket) == FinalRegistrationTicket:
                ticket.validate(chainwrapper)
            else:
                continue

            regticket = ticket.ticket

            # collect fingerprints
            # TODO: only collect this for activated regtickets and tickets not older than X blocks
            fingerprint_db[regticket.imagedata_hash] = ("DUMMY_PATH", regticket.fingerprints)  # TODO: do we need this?

            # validate that this art hash does not yet exist on the blockchain
            # TODO: only prohibit registration when this was registered in the past X blocks
            # TODO: if regticket is activated: prohibit registration forever
            require_true(regticket.imagedata_hash != self.imagedata_hash)

        # validate that fingerprints are not dupes
        if len(fingerprint_db) > 0:
            # TODO: check for fingerprint dupes
            if NetWorkSettings.DUPE_DETECTION_ENABLED:
                pandas_table = assemble_fingerprints_for_pandas([(k, v) for k, v in fingerprint_db.items()])
                is_duplicate, params_df = measure_similarity(self.fingerprints, pandas_table)
                if is_duplicate:
                    raise ValueError("Image failed fingerprint check!")


class ActivationTicket(TicketModelBase):
    methods = {
        # mandatory fields for Final Ticket
        "author": PubkeyField(),
        "order_block_txid": TXIDField(),

        "registration_ticket_txid": TXIDField(),
    }

    def validate(self, chainwrapper, image):
        # TODO:
        # X validate that this ticket references a valid regticket
        #   X regticket is on chain
        #   X regticket is not yet activated
        #   X regticket signatures are valid
        # X validate metadata:
        #   X fingerprints matches image
        #   X lubyhashes matches image
        #   X thumbnailhash matches image
        # X validate image
        #   X image actually hashes to imagedata_hash in the regticket
        #   X image is sfw
        #   X luby chunks generate the image

        # TODO: check that final_regticket ticket is not activated yet

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


class TradeTicket(TicketModelBase):
    methods = {
        "public_key": PubkeyField(),
        "imagedata_hash": SHA3512Field(),
        "type": StringChoiceField(choices=["ask", "bid"]),
        "copies": IntegerField(minsize=0, maxsize=1000),
        "price": IntegerField(minsize=0, maxsize=2 ** 32 - 1),
        "watched_address": BlockChainAddressField(),
        "collateral_txid": TXIDField(),
        "expiration": IntegerField(minsize=0, maxsize=1000),  # x==0 means never expire, x > 0 mean X blocks
    }

    def validate(self, blockchain, chainwrapper, artregistry):
        # make sure artwork is properly registered
        artregistry.get_ticket_for_artwork(self.imagedata_hash)

        # if this is a bid, validate collateral
        if self.type == "bid":
            # does the collateral utxo exist?
            transaction = blockchain.getrawtransaction(self.collateral_txid, 1)

            # is the utxo a new one we are not currently watching? - this is to prevent a user reusing a collateral
            _, listen_utxos = artregistry.get_listen_addresses_and_utxos()
            require_true(self.collateral_txid not in listen_utxos)

            # validate collateral
            valid = False
            for vout in transaction["vout"]:
                if len(vout["scriptPubKey"]["addresses"]) > 1:
                    continue

                # validate address and amount of collateral
                value = vout["value"]
                address = vout["scriptPubKey"]["addresses"][0]
                if address == self.watched_address and value == self.copies * self.price:
                    valid = True
                    break

            if not valid:
                raise ValueError("UTXO does not contain valid address as vout")

        # we can't validate anything else here as all other checks are dependent on other tickets:
        #  o copies is dependent on the current order book
        #  o price can be anything
        #  o expiration is time dependent


class TransferTicket(TicketModelBase):
    methods = {
        "public_key": PubkeyField(),
        "recipient": PubkeyField(),
        "imagedata_hash": SHA3512Field(),
        "copies": IntegerField(minsize=0, maxsize=1000),
    }

    def validate(self, chainwrapper, artregistry):
        # make sure artwork is properly registered
        artregistry.get_ticket_for_artwork(self.imagedata_hash)

        # we can't validate anything else here as all other checks are dependent on other tickets:
        #  o public_key might not own any more copies
        #  o recipient can be any key
        #  o copies depends on whether public_key owns enough copies which is time dependent


class IDTicket(TicketModelBase):
    methods = {
        # mandatory fields for Final Ticket
        "blockchain_address": BlockChainAddressField(),
        "public_key": PubkeyField(),
        "ticket_submission_time": UnixTimeField(),
    }

    def validate(self):
        # TODO: finish
        # Validate:
        #  o x time hasn't passed
        #  o x blocks hasn't passed
        #  o blockchain address is legit
        pass


class Signature(TicketModelBase):
    methods = {
        "signature": SignatureField(),
        "pubkey": PubkeyField(),
    }

    def validate(self, ticket):
        if not pastel_id_verify_signature_with_public_key_func(ticket.serialize(), self.signature, self.pubkey):
            raise ValueError("Invalid signature")


class MasterNodeSignedTicket(TicketModelBase):
    def validate(self, chainwrapper):
        # validate that the author is correct and pubkeys match MNs
        if self.signature_author.pubkey != self.ticket.author:
            raise ValueError("Signature pubkey does not match regticket.author!")

        # prevent nonce reuse
        require_true(chainwrapper.valid_nonce(self.nonce))

        if NetWorkSettings.VALIDATE_MN_SIGNATURES:
            # validate masternode order that's in the ticket
            masternode_ordering = chainwrapper.masternode_workers(self.ticket.blocknum)

            # make sure we got 3 MNs
            if len(masternode_ordering) != 3:
                raise ValueError("Incorrect masternode list returned by get_masternode_order: %s" % masternode_ordering)

            # make sure they're unique
            if len(set([x['IP:port'] for x in masternode_ordering])) != 3:
                raise ValueError(
                    "Masternodes are not unique as returned by get_masternode_order: %s" % masternode_ordering)

            if (self.signature_1.pubkey != base64.b64decode(masternode_ordering[0]['pyPubKey']) or
                    self.signature_2.pubkey != base64.b64decode(masternode_ordering[1]['pyPubKey']) or
                    self.signature_3.pubkey != base64.b64decode(masternode_ordering[2]['pyPubKey'])):
                raise ValueError("Invalid pubkey for masternode ordering")

            # validate signatures
            self.signature_author.validate(self.ticket)
            self.signature_1.validate(self.ticket)
            self.signature_2.validate(self.ticket)
            self.signature_3.validate(self.ticket)
        else:
            # we are running in debug mode, do not check signatures
            pass

        # TODO: make sure the ticket was paid for


class SelfSignedTicket(TicketModelBase):
    def validate(self, chainwrapper):
        # validate that the author is correct and pubkeys match MNs
        if self.signature.pubkey != self.ticket.public_key:
            raise ValueError("Signature pubkey does not match regticket.author!")

        # prevent nonce reuse
        require_true(chainwrapper.valid_nonce(self.nonce))


class FinalIDTicket(SelfSignedTicket):
    methods = {
        "ticket": IDTicket,
        "signature": Signature,
        "nonce": UUIDField(),
    }


class FinalTradeTicket(SelfSignedTicket):
    # TODO: this should be a MasterNodeSignedTicket, although that provides no tangible benefits here
    methods = {
        "ticket": TradeTicket,
        "signature": Signature,
        "nonce": UUIDField(),
    }


class FinalTransferTicket(SelfSignedTicket):
    # TODO: this should be a MasterNodeSignedTicket, although that provides no tangible benefits here
    methods = {
        "ticket": TransferTicket,
        "signature": Signature,
        "nonce": UUIDField(),
    }


class FinalRegistrationTicket(MasterNodeSignedTicket):
    methods = {
        "ticket": RegistrationTicket,
        "signature_author": Signature,
        "signature_1": Signature,
        "signature_2": Signature,
        "signature_3": Signature,
        "nonce": UUIDField(),
    }


class FinalActivationTicket(MasterNodeSignedTicket):
    methods = {
        "ticket": ActivationTicket,
        "signature_author": Signature,
        "signature_1": Signature,
        "signature_2": Signature,
        "signature_3": Signature,
        "nonce": UUIDField(),
    }
# ===== END ===== #
