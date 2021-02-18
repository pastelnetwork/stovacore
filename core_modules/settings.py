"""
Pynode settings, config parsing.
"""
import configparser

import math
import os
import hashlib


class ConfigIsNotSet(Exception):
    pass


LOG_DESTINATION_STDOUT = 'stdout'


# SETTINGS - global settings for everyone
class __Settings:
    def __init__(self):
        if os.environ.get('PYNODE_MODE') != 'WALLET':
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

            print('Reading configuration at {}'.format(self.config_filename))

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
            if 'log_destination' in section:
                self.LOG_DESTINATION = section['log_destination']
            else:
                self.LOG_DESTINATION = LOG_DESTINATION_STDOUT
            self.LOG_LEVEL = section['log_level']
        else:
            self.IS_TESTNET = True
            self.LOG_LEVEL = 'debug'

        # hardcoded settings
        self.DEBUG = False
        BASEDIR = os.path.abspath(os.path.join(__file__, "..", ".."))
        self.NSFW_MODEL_FILE = os.path.join(BASEDIR, "misc", "nsfw_trained_model.pb")
        self.PASTEL_DIR = os.path.join(os.getenv('HOME'), '.pastel')

        self.HTTPS_CERT_DIR = os.path.join(self.PASTEL_DIR, 'pynode_https_cert')
        self.HTTPS_KEY_FILE = os.path.join(self.HTTPS_CERT_DIR, 'privkey.pem')
        self.HTTPS_CERTIFICATE_FILE = os.path.join(self.HTTPS_CERT_DIR, 'certificate.pem')
        self.MN_DATABASE_FILE = os.path.join(self.PASTEL_DIR, 'masternode.db')
        self.RPC_PORT = '4444'
        self.CNODE_RPC_USER = 'rt'
        self.CNODE_RPC_PWD = 'rt'
        self.CNODE_RPC_IP = '127.0.0.1'
        self.CNODE_RPC_PORT = 19932 if self.IS_TESTNET else 9932
        print('Pynode confguration initialized')


Settings = __Settings()

Settings.CNODE_HASH_ALGO = hashlib.sha256
Settings.PYNODE_HASH_ALGO = hashlib.sha3_512
Settings.CNODE_HEX_DIGEST_SIZE = Settings.CNODE_HASH_ALGO().digest_size * 2
Settings.PYNODE_HEX_DIGEST_SIZE = Settings.PYNODE_HASH_ALGO().digest_size * 2

Settings.RPC_MSG_SIZELIMIT = 100 * 1024 * 1024  # 100MB

Settings.REPLICATION_FACTOR = 7
Settings.CHUNKSIZE = 1 * 1024 * 1024  # 1MB
Settings.CHUNK_FETCH_PARALLELISM = 15  # we will fetch this many chunks simultaneously in coroutines

Settings.IMAGE_MAX_SIZE = 100 * 1024 * 1024  # 100MB

Settings.MAX_REGISTRATION_BLOCK_DISTANCE = 10000000  # blocks

Settings.THUMBNAIL_DIMENSIONS = (240, 240)
Settings.THUMBNAIL_MAX_SIZE = 300 * 1024  # 300 KB

Settings.LUBY_REDUNDANCY_FACTOR = 10

Settings.MAX_LUBY_CHUNKS = math.ceil((Settings.IMAGE_MAX_SIZE / Settings.CHUNKSIZE) \
                                     * Settings.LUBY_REDUNDANCY_FACTOR)

Settings.NSFW_THRESHOLD = 1 if Settings.DEBUG else 0.99

Settings.DUPE_DETECTION_ENABLED = not Settings.DEBUG  # False if DEBUG, True for production

Settings.DUPE_DETECTION_MODELS = ["VGG16"]
Settings.DUPE_DETECTION_FINGERPRINT_SIZE = 512

Settings.DUPE_DETECTION_TARGET_SIZE = (240, 240)  # the dupe detection modules were trained with this size
Settings.DUPE_DETECTION_SPEARMAN_THRESHOLD = 0.86
Settings.DUPE_DETECTION_KENDALL_THRESHOLD = 0.80
Settings.DUPE_DETECTION_HOEFFDING_THRESHOLD = 0.48
Settings.DUPE_DETECTION_STRICTNESS = 0.99
Settings.DUPE_DETECTION_KENDALL_MAX = 0
Settings.DUPE_DETECTION_HOEFFDING_MAX = 0


Settings.MAX_CONFIRMATION_DISTANCE_IN_BLOCKS = 2000  # blocks
