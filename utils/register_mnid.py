from cnode_connection import get_blockchain_connection
from core_modules.blockchain import DEFAULT_PASTEL_ID_PASSPHRASE

pastelid_list = get_blockchain_connection().pastelid_list()
if not len(pastelid_list):
    raise Exception('There is no pastel IDs on this node. Please register one first.')
else:
    pastelid = pastelid_list[0]['PastelID']
response = get_blockchain_connection().mnid_register(pastelid, DEFAULT_PASTEL_ID_PASSPHRASE)
