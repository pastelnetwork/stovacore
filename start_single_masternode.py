import time

import bitcoinrpc

from core_modules.blockchain import BlockChain
from core_modules.logger import initlogging
from masternode_prototype.masternode_daemon import MasterNodeDaemon

# TODO: as this code runs a single instance of masternode - some entities definetely
# TODO: should be global and instantiated only one.
# TODO: this entities are:
# TODO: - pastelid
# TODO: - passphrase for pastelID
# TODO: - basedir
# TODO: (to be continued)

# TODO: Currently all this entites are instantiated in MasterNodeDaemon class, and are passed through the
# TODO: whole class hierarchy down to the bottom level. It should be fixed.

global_logger = initlogging(int(0), __name__)
global_logger.debug("Started logger")
PASTEL_ID_PASSPHRASE = 'todo_replace_to_some_random_generated_on_startup'


def connect_to_blockchain_daemon():
    while True:
        blockchain = BlockChain(user='rt',
                                password='rt',
                                ip='127.0.0.1',
                                rpcport=19932)
        try:
            blockchain.getwalletinfo()
        except (ConnectionRefusedError, bitcoinrpc.authproxy.JSONRPCException) as exc:
            global_logger.debug("Exception %s while getting wallet info, retrying..." % exc)
            time.sleep(0.5)
        else:
            global_logger.debug("Successfully connected to daemon!")
            break
    return blockchain


def get_or_create_pastel_id(bc):
    pastelid_list = bc.pastelid_list()

    if not len(pastelid_list):
        result = bc.pastelid_newkey(PASTEL_ID_PASSPHRASE)
        return result['pastelid']
    else:
        return pastelid_list[0]['PastelID']


blockchain = connect_to_blockchain_daemon()

# pastelid contains bitcoin-address-encoded PastelID public key.
# It is used in sign/verify interactions with cNode exactly in a given format
pastelid = get_or_create_pastel_id(blockchain)

if __name__ == "__main__":
    mnd = MasterNodeDaemon()
    mnd.run_event_loop()
