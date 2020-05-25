import os
from cnode_connection import get_blockchain_connection
from core_modules.blockchain import DEFAULT_PASTEL_ID_PASSPHRASE

os.environ.setdefault('PASTEL_ID', 'fakepastelid')

get_blockchain_connection().pastelid_newkey(DEFAULT_PASTEL_ID_PASSPHRASE)
