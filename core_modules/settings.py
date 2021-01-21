import math
import os
import hashlib
import sys

from decimal import Decimal

from core_modules.helpers_type import ensure_type_of_field


# SETTINGS - global settings for everyone
class __Settings:
    pass


if getattr(sys, 'frozen', False):
    FROZEN = True
else:
    FROZEN = False

Settings = __Settings()

Settings.DEBUG = False
Settings.LOG_LEVEL = 'debug'

Settings.FROZEN = FROZEN
Settings.BASEDIR = os.path.abspath(os.path.join(__file__, "..", ".."))
Settings.CHROOT_DIR = os.path.join(Settings.BASEDIR, "chroot_dir")
Settings.NSFW_MODEL_FILE = os.path.join(Settings.BASEDIR, "misc", "nsfw_trained_model.pb")

Settings.UNSHARE_CMDLINE = ["unshare", "-mUuinpCrf", "--mount-proc=/proc", "--"]

if FROZEN:
    Settings.IMAGEPARSERCMDLINE = Settings.UNSHARE_CMDLINE + [
        os.path.join(Settings.BASEDIR, "parse_image_in_jail")]
else:
    Settings.IMAGEPARSERCMDLINE = Settings.UNSHARE_CMDLINE + [
        "python", os.path.join(Settings.BASEDIR, "parse_image_in_jail.py")]

Settings.IMAGE_PARSER_TIMEOUT_SECONDS = 3

Settings.VALIDATE_MN_SIGNATURES = True

Settings.COIN = Decimal('100000')
Settings.BASE_TRANSACTION_AMOUNT = Decimal('300.0') / Decimal(Settings.COIN)  # 0.00300
Settings.FEEPERKB = Decimal('0.0001')

Settings.TICKET_MATCH_EXPIRY = 30  # 30s blocks x 30: 900s -> 15m

if Settings.DEBUG:
    Settings.REQUIRED_CONFIRMATIONS = 1
else:
    # Settings.REQUIRED_CONFIRMATIONS = 10
    Settings.REQUIRED_CONFIRMATIONS = 1

# We set this so low, because we don't care if the utxo gets invalidated. If it does, the ticket is lost anyway and
# we need to be as fast as possible here.
Settings.REQUIRED_CONFIRMATIONS_FOR_TRADE_UTXO = 1

Settings.ALIAS_SEED = b'd\xad`n\xdc\x89\xc2/\xf6\xcd\xd6\xec\xcc\x1c\xc7\xd4\x83B9\x01\xb4\x06\xa2\xc9=\xf8_\x98\xa1p\x01&'
Settings.CNODE_HASH_ALGO = hashlib.sha256
Settings.PYNODE_HASH_ALGO = hashlib.sha3_512
Settings.CNODE_HEX_DIGEST_SIZE = Settings.CNODE_HASH_ALGO().digest_size * 2
Settings.PYNODE_HEX_DIGEST_SIZE = Settings.PYNODE_HASH_ALGO().digest_size * 2

# TODO: set this to something more reasonable, perhaps set it per RPC call with ACLs?
Settings.RPC_MSG_SIZELIMIT = 100 * 1024 * 1024  # 100MB

Settings.REPLICATION_FACTOR = 15
Settings.CHUNKSIZE = 1 * 1024 * 1024  # 1MB
Settings.CHUNK_REFETCH_INTERVAL = 60  # do not retry to fetch chunk unless this many seconds elapsed
Settings.CHUNK_FETCH_PARALLELISM = 15  # we will fetch this many chunks simultaneously in coroutines

Settings.MAX_TICKET_SIZE = 75 * 1024  # 75kbyte
Settings.IMAGE_MAX_SIZE = 100 * 1024 * 1024  # 100MB
# FIXME: MAX_REGISTRATION_BLOCK_DISTANCE increased from 3 to 10 cause ticket validation function is too slow for 3 blocks.
# Settings.MAX_REGISTRATION_BLOCK_DISTANCE = 3  # 3 blocks
# Settings.MAX_REGISTRATION_BLOCK_DISTANCE = 10  # 3 blocks
Settings.MAX_REGISTRATION_BLOCK_DISTANCE = 10000000  # 3 blocks

Settings.THUMBNAIL_DIMENSIONS = (240, 240)
Settings.THUMBNAIL_MAX_SIZE = 200 * 1024  # 200 kb

Settings.LUBY_REDUNDANCY_FACTOR = 10

Settings.MAX_LUBY_CHUNKS = math.ceil((Settings.IMAGE_MAX_SIZE / Settings.CHUNKSIZE) \
                                            * Settings.LUBY_REDUNDANCY_FACTOR)

if Settings.DEBUG:
    Settings.NSFW_THRESHOLD = 1
else:
    Settings.NSFW_THRESHOLD = 0.99

if Settings.DEBUG:
    Settings.DUPE_DETECTION_ENABLED = False
    Settings.DUPE_DETECTION_MODELS = ["VGG16"]
    Settings.DUPE_DETECTION_FINGERPRINT_SIZE = 512
    # Settings.DUPE_DETECTION_MODELS = ["VGG16", "Xception", "InceptionResNetV2", "DenseNet201", "InceptionV3"]
    # Settings.DUPE_DETECTION_FINGERPRINT_SIZE = 8064
else:
    Settings.DUPE_DETECTION_ENABLED = True
    Settings.DUPE_DETECTION_MODELS = ["VGG16"]
    # Settings.DUPE_DETECTION_MODELS = ["VGG16", "Xception", "InceptionResNetV2", "DenseNet201", "InceptionV3"]
    # Settings.DUPE_DETECTION_FINGERPRINT_SIZE = 8064
    Settings.DUPE_DETECTION_FINGERPRINT_SIZE = 512

Settings.DUPE_DETECTION_TARGET_SIZE = (240, 240)  # the dupe detection modules were trained with this size
Settings.DUPE_DETECTION_SPEARMAN_THRESHOLD = 0.86
Settings.DUPE_DETECTION_KENDALL_THRESHOLD = 0.80
Settings.DUPE_DETECTION_HOEFFDING_THRESHOLD = 0.48
Settings.DUPE_DETECTION_STRICTNESS = 0.99
Settings.DUPE_DETECTION_KENDALL_MAX = 0
Settings.DUPE_DETECTION_HOEFFDING_MAX = 0

Settings.RPC_PORT = '4444'

Settings.PASTEL_DIR = os.path.join(os.getenv('HOME'), '.pastel')
Settings.CHUNK_DATA_DIR = os.path.join(Settings.BASEDIR, "chunkdata")
Settings.TEMP_STORAGE_DIR = os.path.join(Settings.BASEDIR, "tmpstorage")

Settings.HTTPS_KEY_FILE = os.path.join(Settings.PASTEL_DIR, 'privkey.pem')
Settings.HTTPS_CERTIFICATE_FILE = os.path.join(Settings.PASTEL_DIR, 'certificate.pem')

Settings.MN_DATABASE_FILE = os.path.join(Settings.PASTEL_DIR, 'masternode.db')
Settings.LONG_REGTICKET_VALIDATION_ENABLED = False

# FIXME: change to more appropriate for production usage value
Settings.MAX_CONFIRMATION_DISTANCE_IN_BLOCKS = 2000

Settings.CNODE_RPC_USER = 'rt'
Settings.CNODE_RPC_PWD = 'rt'
Settings.CNODE_RPC_IP = '127.0.0.1'
Settings.CNODE_RPC_PORT = 19932
