import base64
import io
import msgpack

from PIL import Image

from cnode_connection import get_blockchain_connection
from core_modules.helpers import get_pynode_digest_bytes, require_true
from core_modules.logger import initlogging
from core_modules.model_validators import FieldValidator, StringField, IntegerField, FingerprintField, SHA3512Field, \
    LubyChunkHashField, LubyChunkField, ImageField, ThumbnailField, TXIDField, UUIDField, SignatureField, \
    PastelIDField, LubySeedField, BlockChainAddressField, UnixTimeField, StringChoiceField

from core_modules.blackbox_modules.dupe_detection_utils import measure_similarity, assemble_fingerprints_for_pandas
from core_modules.settings import NetWorkSettings

from core_modules.blackbox_modules.nsfw import get_nsfw_detector

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

    def serialize_base64(self):
        return base64.b64encode(self.serialize()).decode()

    def unserialize(self, packed):
        return msgpack.unpackb(packed, raw=False)

    def unserialize_base64(self, b64_packed):
        return self.unserialize(base64.b64decode(b64_packed))

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
        from utils.dupe_detection import DupeDetector
        fingerprints = DupeDetector(NetWorkSettings.DUPE_DETECTION_MODELS,
                                    NetWorkSettings.DUPE_DETECTION_TARGET_SIZE).compute_deep_learning_features(
            self.image)
        return fingerprints

    @staticmethod
    def generate_luby_chunks(imagedata, seeds=None):
        chunks = luby.encode(NetWorkSettings.LUBY_REDUNDANCY_FACTOR, NetWorkSettings.CHUNKSIZE, imagedata, seeds)

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
        "author": PastelIDField(),
        # "author_wallet": BlockChainAddressField(),
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
        block_distance = chainwrapper.get_block_distance(get_blockchain_connection().getbestblockhash(), self.order_block_txid)
        if block_distance > NetWorkSettings.MAX_REGISTRATION_BLOCK_DISTANCE:
            raise ValueError("Block distance between order_block_height and current block is too large!")
        # validate that art hash doesn't exist:
        # TODO: move this artwork index logic into chainwrapper
        fingerprint_db = {}

        # validate that fingerprints are not dupes
        if len(fingerprint_db) > 0:
            # TODO: check for fingerprint dupes
            if NetWorkSettings.DUPE_DETECTION_ENABLED:
                pandas_table = assemble_fingerprints_for_pandas([(k, v) for k, v in fingerprint_db.items()])
                is_duplicate, params_df = measure_similarity(self.fingerprints, pandas_table)
                if is_duplicate:
                    raise ValueError("Image failed fingerprint check!")

    @property
    def base64_imagedatahash(self):
        return base64.b64encode(self.imagedata_hash).decode()


class TradeTicket(TicketModelBase):
    methods = {
        "public_key": PastelIDField(),
        "imagedata_hash": SHA3512Field(),
        "type": StringChoiceField(choices=["ask", "bid"]),
        "copies": IntegerField(minsize=0, maxsize=1000),
        "price": IntegerField(minsize=0, maxsize=2 ** 32 - 1),
        "watched_address": BlockChainAddressField(),
        "collateral_txid": TXIDField(),
        "expiration": IntegerField(minsize=0, maxsize=1000),  # x==0 means never expire, x > 0 mean X blocks
    }

    def validate(self, chainwrapper, artregistry):
        # make sure artwork is properly registered
        artregistry.get_ticket_for_artwork(self.imagedata_hash)

        # if this is a bid, validate collateral
        if self.type == "bid":
            # does the collateral utxo exist?
            transaction = get_blockchain_connection().getrawtransaction(self.collateral_txid, 1)

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
        "public_key": PastelIDField(),
        "recipient": PastelIDField(),
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
        "public_key": PastelIDField(),
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
        "pastelid": PastelIDField(),
    }

    def validate(self, ticket):
        if not get_blockchain_connection().pastelid_verify(ticket.serialize_base64(), self.signature, self.pastelid):
            raise ValueError("Invalid signature")


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

# ===== END ===== #
