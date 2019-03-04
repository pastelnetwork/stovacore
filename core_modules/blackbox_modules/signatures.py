import random
import time

from .crypto import get_Ed521

Ed521 = get_Ed521()


def pastel_id_write_signature_on_data_func(data, private_key, public_key):
    if type(data) != bytes or type(private_key) != bytes or type(public_key) != bytes:
        raise TypeError("All arguments must be bytes, were: %s %s %s" % (type(data), type(private_key), type(public_key)))

    time.sleep(0.1 * random.random())  # To combat side-channel attacks
    signature = bytes(Ed521.sign(private_key, public_key, data))
    time.sleep(0.1 * random.random())
    return signature


def pastel_id_verify_signature_with_public_key_func(data, signature, public_key):
    if type(data) != bytes or type(signature) != bytes or type(public_key) != bytes:
        raise TypeError("All arguments must be bytes, were: %s %s %s" % (type(data), type(signature), type(public_key)))

    time.sleep(0.1 * random.random())
    verified = Ed521.verify(public_key, data, signature)
    time.sleep(0.1 * random.random())
    return verified
