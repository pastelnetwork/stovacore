import nacl

from nacl import utils

from .crypto import get_Ed521

Ed521 = get_Ed521()


def id_keypair_generation_func():
    input_length = 521*2
    private_key, public_key = Ed521.keygen(nacl.utils.random(input_length))
    return private_key, bytes(public_key)
