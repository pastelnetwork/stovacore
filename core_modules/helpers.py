import random

from .settings import NetWorkSettings

CNODE_HASH_ALGO = NetWorkSettings.CNODE_HASH_ALGO
PYNODE_HASH_ALGO = NetWorkSettings.PYNODE_HASH_ALGO
SHA2_HEXFORMAT = "%0" + str(NetWorkSettings.CNODE_HEX_DIGEST_SIZE) + "x"
SHA3_HEXFORMAT = "%0" + str(NetWorkSettings.PYNODE_HEX_DIGEST_SIZE) + "x"


def getrandbytes(n):
    return random.getrandbits(n * 8).to_bytes(n, byteorder="big")


def get_cnode_digest_bytes(data):
    h = CNODE_HASH_ALGO()
    h.update(data)
    return h.digest()


def get_cnode_digest_hex(data):
    h = CNODE_HASH_ALGO()
    h.update(data)
    return h.hexdigest()


def get_pynode_digest_bytes(data: bytes) -> bytes:
    h = PYNODE_HASH_ALGO()  # hashlib.sha3_512
    h.update(data)  # -> hashlib.sha3_512.update(data)
    return h.digest()


def get_pynode_digest_hex(data):
    h = PYNODE_HASH_ALGO()
    h.update(data)
    return h.hexdigest()


def get_pynode_digest_int(data):
    h = PYNODE_HASH_ALGO()
    h.update(data)
    return int.from_bytes(h.digest(), byteorder="big")


def get_nodeid_from_pubkey(data):
    h = PYNODE_HASH_ALGO()
    h.update(data)
    return int.from_bytes(h.digest(), byteorder="big")


def hex_to_chunkid(digest):
    return int(digest, 16)


def hex_to_pubkey(digest):
    return int(digest, 16)


def chunkid_to_hex(digest):
    return SHA3_HEXFORMAT % digest


def bytes_to_chunkid(data):
    return int(data.hex(), 16)


def bytes_from_hex(data):
    return bytes.fromhex(data)


def bytes_to_hex(data):
    return data.hex()


def bytes_from_int(data):
    return int.from_bytes(data, byteorder="big")


def require_true(param, msg=""):
    # this function replaces the built in assert function so that we can use this in production when ran with
    # optimizations turned on
    if not param:
        raise AssertionError(msg)
