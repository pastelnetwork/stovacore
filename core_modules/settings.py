import configparser

import math
import os
import hashlib

from decimal import Decimal


class ConfigIsNotSet(Exception):
    pass


# SETTINGS - global settings for everyone
class __Settings:
    def __init__(self):
        if 'CONFIG_FILE' not in os.environ:
            raise ConfigIsNotSet(
                'Config file is not set up. Please set environment variable CONFIG_FILE to point the config file')
        self.config_filename = os.environ['CONFIG_FILE']

        if not self.config_filename:
            raise Exception('Settings: config file is not provided')
        if not os.path.isfile(self.config_filename):
            raise Exception(
                'Unable to read the config at "{}". Please check if it exists and has appropriate permissions'.format(
                    self.config_filename))
        config = configparser.ConfigParser()
        config.read(self.config_filename)
        if 'default' not in config:
            raise Exception('Config file should have "default" section')
        section = config['default']

        # settings read from config
        self.IS_TESTNET = section.getboolean('testnet')
        self.PASTEL_ID_PASSPHRASE = section['passphrase']
        self.CHUNK_DATA_DIR = section['storage_dir']
        self.TEMP_STORAGE_DIR = section['tmp_storage_dir']

        # hardcoded settings
        self.DEBUG = False
        self.LOG_LEVEL = 'debug'
        BASEDIR = os.path.abspath(os.path.join(__file__, "..", ".."))
        self.NSFW_MODEL_FILE = os.path.join(BASEDIR, "misc", "nsfw_trained_model.pb")
        self.PASTEL_DIR = os.path.join(os.getenv('HOME'), '.pastel')

        self.HTTPS_CERT_DIR = os.path.join(self.PASTEL_DIR, 'pynode_https_cert')
        self.HTTPS_KEY_FILE = os.path.join(self.HTTPS_CERT_DIR, 'privkey.pem')
        self.HTTPS_CERTIFICATE_FILE = os.path.join(self.HTTPS_CERT_DIR, 'certificate.pem')
        self.MN_DATABASE_FILE = os.path.join(self.PASTEL_DIR, 'masternode.db')


Settings = __Settings()

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


# FIXME: change to more appropriate for production usage value
Settings.MAX_CONFIRMATION_DISTANCE_IN_BLOCKS = 2000

Settings.CNODE_RPC_USER = 'rt'
Settings.CNODE_RPC_PWD = 'rt'
Settings.CNODE_RPC_IP = '127.0.0.1'
Settings.CNODE_RPC_PORT = 19932 if Settings.IS_TESTNET else 9932
