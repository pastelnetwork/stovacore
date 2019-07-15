import math
import os
import hashlib
import sys

from decimal import Decimal

from core_modules.helpers_type import ensure_type_of_field


# NETWORK SETTINGS - global settings for everyone
class __NetworkSettings:
    pass


if getattr(sys, 'frozen', False):
    FROZEN = True
else:
    FROZEN = False

NetWorkSettings = __NetworkSettings()

NetWorkSettings.FROZEN = FROZEN
NetWorkSettings.BASEDIR = os.path.abspath(os.path.join(__file__, "..", ".."))
NetWorkSettings.CHROOT_DIR = os.path.join(NetWorkSettings.BASEDIR, "chroot_dir")
NetWorkSettings.NSFW_MODEL_FILE = os.path.join(NetWorkSettings.BASEDIR, "misc", "nsfw_trained_model.pb")

NetWorkSettings.UNSHARE_CMDLINE = ["unshare", "-mUuinpCrf", "--mount-proc=/proc", "--"]
NetWorkSettings.DEBUG = False

if FROZEN:
    NetWorkSettings.IMAGEPARSERCMDLINE = NetWorkSettings.UNSHARE_CMDLINE + [
        os.path.join(NetWorkSettings.BASEDIR, "parse_image_in_jail")]
else:
    NetWorkSettings.IMAGEPARSERCMDLINE = NetWorkSettings.UNSHARE_CMDLINE + [
        "python", os.path.join(NetWorkSettings.BASEDIR, "parse_image_in_jail.py")]

NetWorkSettings.IMAGE_PARSER_TIMEOUT_SECONDS = 3

NetWorkSettings.VALIDATE_MN_SIGNATURES = True

NetWorkSettings.COIN = Decimal('100000')
NetWorkSettings.BASE_TRANSACTION_AMOUNT = Decimal('300.0') / Decimal(NetWorkSettings.COIN)  # 0.00300
NetWorkSettings.FEEPERKB = Decimal('0.0001')
NetWorkSettings.CDAEMON_CONFIG_FILE = "pastel.conf"

NetWorkSettings.TICKET_MATCH_EXPIRY = 30  # 30s blocks x 30: 900s -> 15m

if NetWorkSettings.DEBUG:
    NetWorkSettings.REQUIRED_CONFIRMATIONS = 1
else:
    # NetWorkSettings.REQUIRED_CONFIRMATIONS = 10
    NetWorkSettings.REQUIRED_CONFIRMATIONS = 1

# We set this so low, because we don't care if the utxo gets invalidated. If it does, the ticket is lost anyway and
# we need to be as fast as possible here.
NetWorkSettings.REQUIRED_CONFIRMATIONS_FOR_TRADE_UTXO = 1

NetWorkSettings.ALIAS_SEED = b'd\xad`n\xdc\x89\xc2/\xf6\xcd\xd6\xec\xcc\x1c\xc7\xd4\x83B9\x01\xb4\x06\xa2\xc9=\xf8_\x98\xa1p\x01&'
NetWorkSettings.CNODE_HASH_ALGO = hashlib.sha256
NetWorkSettings.PYNODE_HASH_ALGO = hashlib.sha3_512
NetWorkSettings.CNODE_HEX_DIGEST_SIZE = NetWorkSettings.CNODE_HASH_ALGO().digest_size * 2
NetWorkSettings.PYNODE_HEX_DIGEST_SIZE = NetWorkSettings.PYNODE_HASH_ALGO().digest_size * 2

# TODO: set this to something more reasonable, perhaps set it per RPC call with ACLs?
NetWorkSettings.RPC_MSG_SIZELIMIT = 100 * 1024 * 1024  # 100MB

NetWorkSettings.REPLICATION_FACTOR = 15
NetWorkSettings.CHUNKSIZE = 1 * 1024 * 1024  # 1MB
NetWorkSettings.CHUNK_REFETCH_INTERVAL = 60  # do not retry to fetch chunk unless this many seconds elapsed
NetWorkSettings.CHUNK_FETCH_PARALLELISM = 15  # we will fetch this many chunks simultaneously in coroutines

NetWorkSettings.MAX_TICKET_SIZE = 75 * 1024  # 75kbyte
NetWorkSettings.IMAGE_MAX_SIZE = 100 * 1024 * 1024  # 100MB
# FIXME: MAX_REGISTRATION_BLOCK_DISTANCE increased from 3 to 10 cause ticket validation function is too slow for 3 blocks.
# NetWorkSettings.MAX_REGISTRATION_BLOCK_DISTANCE = 3  # 3 blocks
NetWorkSettings.MAX_REGISTRATION_BLOCK_DISTANCE = 10  # 3 blocks

NetWorkSettings.THUMBNAIL_DIMENSIONS = (240, 240)
NetWorkSettings.THUMBNAIL_MAX_SIZE = 100 * 1024  # 100 kb

NetWorkSettings.LUBY_REDUNDANCY_FACTOR = 10

NetWorkSettings.MAX_LUBY_CHUNKS = math.ceil((NetWorkSettings.IMAGE_MAX_SIZE / NetWorkSettings.CHUNKSIZE) \
                                            * NetWorkSettings.LUBY_REDUNDANCY_FACTOR)

if NetWorkSettings.DEBUG:
    NetWorkSettings.NSFW_THRESHOLD = 1
else:
    NetWorkSettings.NSFW_THRESHOLD = 0.7

if NetWorkSettings.DEBUG:
    NetWorkSettings.DUPE_DETECTION_ENABLED = False
    NetWorkSettings.DUPE_DETECTION_MODELS = ["VGG16"]
    NetWorkSettings.DUPE_DETECTION_FINGERPRINT_SIZE = 512
    # NetWorkSettings.DUPE_DETECTION_MODELS = ["VGG16", "Xception", "InceptionResNetV2", "DenseNet201", "InceptionV3"]
    # NetWorkSettings.DUPE_DETECTION_FINGERPRINT_SIZE = 8064
else:
    NetWorkSettings.DUPE_DETECTION_ENABLED = True
    NetWorkSettings.DUPE_DETECTION_MODELS = ["VGG16"]
    # NetWorkSettings.DUPE_DETECTION_MODELS = ["VGG16", "Xception", "InceptionResNetV2", "DenseNet201", "InceptionV3"]
    # NetWorkSettings.DUPE_DETECTION_FINGERPRINT_SIZE = 8064
    NetWorkSettings.DUPE_DETECTION_FINGERPRINT_SIZE = 512

NetWorkSettings.DUPE_DETECTION_TARGET_SIZE = (240, 240)  # the dupe detection modules were trained with this size
NetWorkSettings.DUPE_DETECTION_SPEARMAN_THRESHOLD = 0.86
NetWorkSettings.DUPE_DETECTION_KENDALL_THRESHOLD = 0.80
NetWorkSettings.DUPE_DETECTION_HOEFFDING_THRESHOLD = 0.48
NetWorkSettings.DUPE_DETECTION_STRICTNESS = 0.99
NetWorkSettings.DUPE_DETECTION_KENDALL_MAX = 0
NetWorkSettings.DUPE_DETECTION_HOEFFDING_MAX = 0

NetWorkSettings.HTTPS_KEY_FILE = '/home/animecoinuser/.pastel/pynode_https_cert/privkey.pem'
NetWorkSettings.HTTPS_CERTIFICATE_FILE = '/home/animecoinuser/.pastel/pynode_https_cert/certificate.pem'
NetWorkSettings.MN_DATABASE_FILE = '/home/animecoinuser/.pastel/masternode.db'
