# console util for converting ANI private key to PSL private key (has nothing in common with ID!)
# it's built to executable with pyInstaller and called from wallet main process when user tries to import ANI key
import sys

import base58
import hashlib

ANI_PUBKEY_ADDRESS = 23
ANI_SCRIPT_ADDRESS = 9
ANI_PRIVKEY_ADDRESS = ANI_PUBKEY_ADDRESS + 128
ANI_PUBKEY_ADDRESS_TEST = 119
ANI_SCRIPT_ADDRESS_TEST = 199
ANI_PRIVKEY_ADDRESS_TEST = ANI_PUBKEY_ADDRESS_TEST + 128


def ani_key_to_hex(key):
    hexKey = base58.b58decode(key)
    listKey = list(hexKey)
    if listKey[0] not in {ANI_PRIVKEY_ADDRESS, ANI_PRIVKEY_ADDRESS_TEST, ANI_PUBKEY_ADDRESS, ANI_PUBKEY_ADDRESS_TEST,
                          ANI_SCRIPT_ADDRESS, ANI_SCRIPT_ADDRESS_TEST}:
        sys.stderr.write('Unknown key type')
        sys.exit(1)
    raw_key = listKey[1:-4]
    return bytes(raw_key).hex()


# network - "main", "test, "reg"
# type - "address", "secret", "script"
def hex_key_to_psl(hexKey, network, key_type):
    listKey = list(bytes.fromhex(hexKey))
    if key_type == "address":
        if network == "main":
            listKey.insert(0, 0x1c)
            listKey.insert(1, 0xef)
        if network == "test" or network == "reg":
            listKey.insert(0, 0x1c)
            listKey.insert(1, 0xef)
    elif key_type == "secret":
        if network == "main":
            listKey.insert(0, 0x80)
        if network == "test" or network == "reg":
            listKey.insert(0, 0xef)
    elif key_type == "script":
        if network == "main":
            listKey.insert(0, 0x1a)
            listKey.insert(1, 0xF6)
        if network == "test" or network == "reg":
            listKey.insert(0, 0x1D)
            listKey.insert(1, 0x37)
    hash_once = hashlib.sha256(bytes(listKey)).digest()
    hash_twice = hashlib.sha256(hash_once).digest()
    hash4 = list(hash_twice[0:4])
    listKey.extend(hash4)
    return base58.b58encode(bytes(listKey))


# ANI secretkey
# key = "PPufguzVoUYHgyLgonWWdjb6aRHqEvhCCBetno2kgKRZdaGkUn92"


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise Exception('Usage: ./ani_import <key>')

    key = sys.argv[1]
    raw_key = ani_key_to_hex(key)
    psl_key = hex_key_to_psl(raw_key, 'test', 'secret')
    sys.stdout.write(psl_key.decode())
