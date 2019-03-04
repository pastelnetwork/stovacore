import math
import os
import hashlib
import sys

from decimal import Decimal

from core_modules.helpers_type import ensure_type_of_field


class MNDeamonSettings:
    def __init__(self, settings):
        self.cdaemon_conf = ensure_type_of_field(settings, "cdaemon_conf", str)
        self.showmetrics = ensure_type_of_field(settings, "showmetrics", str)
        self.rpcuser = ensure_type_of_field(settings, "rpcuser", str)
        self.rpcpassword = ensure_type_of_field(settings, "rpcpassword", str)
        self.port = ensure_type_of_field(settings, "port", int)
        self.rpcport = ensure_type_of_field(settings, "rpcport", int)
        self.listenonion = ensure_type_of_field(settings, "listenonion", str)
        self.nodename = ensure_type_of_field(settings, "nodename", str)
        self.datadir = ensure_type_of_field(settings, "datadir", str)
        self.basedir = ensure_type_of_field(settings, "basedir", str)
        self.ip = ensure_type_of_field(settings, "ip", str)
        self.pyrpcport = ensure_type_of_field(settings, "pyrpcport", int)
        self.pyhttpadmin = ensure_type_of_field(settings, "pyhttpadmin", int)
        self.pubkey = ensure_type_of_field(settings, "pubkey", str)


# NETWORK SETTINGS - global settings for everyone
class __NetworkSettings:
    pass


if getattr(sys, 'frozen', False):
    FROZEN = True
else:
    FROZEN = False

NetWorkSettings = __NetworkSettings()

NetWorkSettings.BASEDIR = os.path.abspath(os.path.join(__file__, "..", ".."))
NetWorkSettings.CHROOT_DIR = os.path.join(NetWorkSettings.BASEDIR, "chroot_dir")
NetWorkSettings.NSFW_MODEL_FILE = os.path.join(NetWorkSettings.BASEDIR, "misc", "nsfw_trained_model.pb")
NetWorkSettings.DJANGO_ROOT = os.path.join(NetWorkSettings.BASEDIR, "client_prototype", "django_frontend")

NetWorkSettings.UNSHARE_CMDLINE = ["unshare", "-mUuinpCrf", "--mount-proc=/proc", "--"]

if FROZEN:
    NetWorkSettings.DEBUG = True  # TODO: change this to False!
    NetWorkSettings.BLOCKCHAIN_BINARY = os.path.join(NetWorkSettings.BASEDIR, "animecoind", "animecoind")
    NetWorkSettings.DJANGOCMDLINE = [os.path.join(NetWorkSettings.BASEDIR, "start_django")]
    NetWorkSettings.IMAGEPARSERCMDLINE = NetWorkSettings.UNSHARE_CMDLINE + [
        os.path.join(NetWorkSettings.BASEDIR, "parse_image_in_jail")]
else:
    NetWorkSettings.DEBUG = True
    NetWorkSettings.BLOCKCHAIN_BINARY = os.path.join(NetWorkSettings.BASEDIR, "..", "..", "..", "animecoin_blockchain",
                                                     "AnimeCoin", "src", "animecoind")
    NetWorkSettings.DJANGOCMDLINE = ["python", os.path.join(NetWorkSettings.DJANGO_ROOT, "start_django.py")]
    NetWorkSettings.IMAGEPARSERCMDLINE = NetWorkSettings.UNSHARE_CMDLINE + [
        "python", os.path.join(NetWorkSettings.BASEDIR, "parse_image_in_jail.py")]

NetWorkSettings.IMAGE_PARSER_TIMEOUT_SECONDS = 3

if NetWorkSettings.DEBUG:
    NetWorkSettings.VALIDATE_MN_SIGNATURES = False
    try:
        from core_modules.settings_dev import *

        NetWorkSettings.MASTERNODE_LIST = MASTERNODE_LIST
    except (ImportError, NameError):

        NetWorkSettings.MASTERNODE_LIST = [
            [
                b'\x90\xf9\x17T\x1e\xf4\xc0p\xd3\xc4?b\xc8\x86Y\x93\xbeh$@\x86wO\x03\xba\xeeY-$\xa2`\x8e\x93<\xb0\xd8:\x0cF\xa3\x96,\xba4\x86y\x9c\x9aQ\xab2~\xbe\x8e\x02\xc857\x13\xf9vVIN(\x00',
                "127.0.0.1",
                13239
            ],
            [
                b"\x9c\xa0\x90V\xaa\x0c\x10\xca\xddXUG\x92\x11\xa6M\x08w\x14\x84\xd2\xd7\xff\xc7=\x06\xc2j.\x8b\x12\xa0)L\xee\x97B\xc4\xdf\xd9\xe4\xc9\xed\x9c\xbb\x1c\xa0\x98'\xe4\r\x8el$\xea\r?\x0f\x81b\x9d\xce\xc5\xa6o\x80",
                "127.0.0.1",
                13240,
            ],
            [
                b'\xaav\x91p\xf6_\xb3\x1a\xaa\x1f2\xf7\xbdD\x86L\'Sv\x1cV/\x8f|h\xc6=\x86a^QM\xeb\x10\x1b\xa28y,\xddP;\xe84W\xaeI\xc8\x00t\xe0k\xe0\x1a\x88\xf1%."\x88\xfd\xad\xbd?\xe3\x01',
                "127.0.0.1",
                13241,
            ],
        ]
else:
    NetWorkSettings.VALIDATE_MN_SIGNATURES = True

NetWorkSettings.COIN = Decimal('100000')
NetWorkSettings.BASE_TRANSACTION_AMOUNT = Decimal('300.0') / Decimal(NetWorkSettings.COIN)  # 0.00300
NetWorkSettings.FEEPERKB = Decimal('0.0001')
NetWorkSettings.CDAEMON_CONFIG_FILE = "animecoin.conf"

NetWorkSettings.TICKET_MATCH_EXPIRY = 30  # 30s blocks x 30: 900s -> 15m

if NetWorkSettings.DEBUG:
    NetWorkSettings.REQUIRED_CONFIRMATIONS = 1
else:
    NetWorkSettings.REQUIRED_CONFIRMATIONS = 10

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
NetWorkSettings.MAX_REGISTRATION_BLOCK_DISTANCE = 3  # 3 blocks

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
    NetWorkSettings.DUPE_DETECTION_MODELS = ["VGG16", "Xception", "InceptionResNetV2", "DenseNet201", "InceptionV3"]
    NetWorkSettings.DUPE_DETECTION_FINGERPRINT_SIZE = 8064

NetWorkSettings.DUPE_DETECTION_TARGET_SIZE = (240, 240)  # the dupe detection modules were trained with this size
NetWorkSettings.DUPE_DETECTION_SPEARMAN_THRESHOLD = 0.86
NetWorkSettings.DUPE_DETECTION_KENDALL_THRESHOLD = 0.80
NetWorkSettings.DUPE_DETECTION_HOEFFDING_THRESHOLD = 0.48
NetWorkSettings.DUPE_DETECTION_STRICTNESS = 0.99
NetWorkSettings.DUPE_DETECTION_KENDALL_MAX = 0
NetWorkSettings.DUPE_DETECTION_HOEFFDING_MAX = 0

if NetWorkSettings.DEBUG:
    NetWorkSettings.BLOCKCHAIN_SEED_ADDR = "127.0.0.1:12340"
else:
    # TODO: fill this out for prod
    NetWorkSettings.BLOCKCHAIN_SEED_ADDR = ""
# END
