"""
Message serialization and signing logic based on MSGPack
"""
from typing import Optional

import nacl.utils
import time
import msgpack

from decimal import Decimal
from copy import copy

from core_modules.helpers import get_pynode_digest_bytes, get_pynode_digest_bytes_base64, ensure_type, \
    ensure_type_of_field
from core_modules.helpers import require_true
from core_modules.settings import Settings
from cnode_connection import get_blockchain_connection

MAX_SUPPORTED_VERSION = 1
NONCE_LENGTH = 32

VALID_CONTAINER_KEYS_v1 = {"version", "sender_id", "receiver_id", "data", "nonce", "timestamp", "signature"}


# START MSGPACK EXT TYPES
# NOTE: Be very careful here when adding new types. Deserializing data from the wire can
#       introduce arbitrary code execution and other nasty things!
#       Decimal, however is not vulnerable to this.
def default(obj):
    if isinstance(obj, Decimal):
        return msgpack.ExtType(0, str(obj).encode("utf-8"))
    raise TypeError("Unknown type: %r" % (obj,))


def ext_hook(code, data):
    if code == 0:
        return Decimal(data.decode("utf-8"))
    return msgpack.ExtType(code, data)


# END MSGPACK EXT TYPES


def ensure_types_for_v1(container):
    sender_id = ensure_type_of_field(container, "sender_id", str)
    receiver_id = ensure_type_of_field(container, "receiver_id", str)
    data = ensure_type_of_field(container, "data", list)
    nonce = ensure_type_of_field(container, "nonce", bytes)
    timestamp = ensure_type_of_field(container, "timestamp", float)
    signature = ensure_type_of_field(container, "signature", str)
    return sender_id, receiver_id, data, nonce, timestamp, signature


def validate_container_format(container: dict) -> bool:
    ensure_type(container, dict)

    if container.get("version") is None:
        raise ValueError("version field must be supported in all containers!")

    version = ensure_type_of_field(container, "version", int)

    if version > MAX_SUPPORTED_VERSION:
        raise NotImplementedError("version %s not implemented, is larger than %s" % (version, MAX_SUPPORTED_VERSION))

    if version == 1:
        # validate all keys for this version
        a, b = set(container.keys()), VALID_CONTAINER_KEYS_v1
        if len(a - b) + len(b - a) > 0:
            raise KeyError("Keys don't match %s != %s" % (a, b))

        # typecheck all the fields
        ensure_types_for_v1(container)
        return True
    else:
        raise NotImplementedError("version %s not implemented" % version)


class RPCMessage:
    def __init__(self, data: list, receiver_pastel_id: str, version: int = MAX_SUPPORTED_VERSION,
                 container: Optional[dict] = None):
        """
        Must be created without `container` argument on client side and with one on server side.
        """
        self.data = data
        self.receiver_pastel_id = receiver_pastel_id
        self.version = version
        if container and (container['data'] != self.data or container['receiver_id'] != receiver_pastel_id):
            raise ValueError('Data in container and data/receiver_pastel_id does must match!')

        self.container = container if container is not None else {
            "version": self.version,
            "sender_id": get_blockchain_connection().pastelid,
            "receiver_id": self.receiver_pastel_id,
            "data": self.data,
            "nonce": nacl.utils.random(NONCE_LENGTH),
            "timestamp": time.time(),
            "signature": '',
        }
        self.sender_id = self.container['sender_id']

    @staticmethod
    def reconstruct(serialized: bytes) -> 'RPCMessage':
        if len(serialized) > Settings.RPC_MSG_SIZELIMIT:
            raise ValueError("Message is too large: %s > %s" % (len(serialized),
                                                                Settings.RPC_MSG_SIZELIMIT))

        container = msgpack.unpackb(serialized, ext_hook=ext_hook, raw=False)
        if not validate_container_format(container):
            raise ValueError('Invalid container format')

        # validate receiver id is us
        if container['receiver_id'] != get_blockchain_connection().pastelid:
            raise ValueError(
                "receiver_id is not us (%s != %s)" % (container['receiver_id'], get_blockchain_connection().pastelid))

        require_true(container['timestamp'] > time.time() - 60)
        require_true(container['timestamp'] < time.time() + 60)

        return RPCMessage(container['data'], container['receiver_id'], container=container)

    def sign(self) -> None:
        """
        Adds signature to the container if one not added yet.
        """
        if self.container['signature']:
            return
        ensure_types_for_v1(self.container)
        container_serialized = msgpack.packb(self.container, default=default, use_bin_type=True)
        self.container['signature'] = get_blockchain_connection().pastelid_sign(
            get_pynode_digest_bytes_base64(container_serialized))

    def pack(self) -> bytes:
        if not self.container['signature']:
            self.sign()

        return msgpack.packb(self.container, default=default, use_bin_type=True)

    def verify(self) -> bool:
        """
        Verify sender signature
        """
        # remove signature from container
        # msgpack it, get digest, verify
        container = copy(self.container)
        signature = container['signature']
        container['signature'] = ''
        container_serialized = msgpack.packb(container, default=default, use_bin_type=True)
        return get_blockchain_connection().pastelid_verify(get_pynode_digest_bytes_base64(container_serialized),
                                                           signature,
                                                           container['sender_id'])
