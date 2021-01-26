import os

from core_modules.settings import Settings

os.environ.setdefault('PASTEL_ID', 'fakepastelid')
os.environ.setdefault('PASSPHRASE', 'fakepassphrase')

from cnode_connection import get_blockchain_connection


get_blockchain_connection().pastelid_newkey(Settings.PASTEL_ID_PASSPHRASE)
