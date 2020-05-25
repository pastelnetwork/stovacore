import os
os.environ.setdefault('PASTEL_ID', 'fakepastelid')
os.environ['PASTEL_ID'] = 'fakepastelid'

from cnode_connection import get_blockchain_connection
from core_modules.blockchain import DEFAULT_PASTEL_ID_PASSPHRASE


get_blockchain_connection().pastelid_newkey(DEFAULT_PASTEL_ID_PASSPHRASE)
