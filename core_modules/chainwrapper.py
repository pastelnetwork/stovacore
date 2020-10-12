from core_modules.helpers import bytes_to_hex
from cnode_connection import get_blockchain_connection


def get_block_distance(atxid, btxid):
    if type(atxid) == bytes:
        atxid = bytes_to_hex(atxid)
    if type(btxid) == bytes:
        btxid = bytes_to_hex(btxid)

    block_a = get_blockchain_connection().getblock(atxid)
    block_b = get_blockchain_connection().getblock(btxid)
    height_a = int(block_a["height"])
    height_b = int(block_b["height"])
    return abs(height_a - height_b)
