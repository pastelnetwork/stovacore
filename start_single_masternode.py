import time

import bitcoinrpc

from core_modules.blockchain import BlockChain
from core_modules.logger import initlogging
from masternode_prototype.masternode_daemon import MasterNodeDaemon

# TODO: as this code runs a single instance of masternode - some entities definetely
# TODO: should be global and instantiated only one.
# TODO: this entities are:
# TODO: - blockchain connection
# TODO: - pastelid
# TODO: - passphrase for pastelID
# TODO: - basedir
# TODO: (to be continued)

# TODO: Currently all this entites are instantiated in MasterNodeDaemon class, and are passed through the
# TODO: whole class hierarchy down to the bottom level. It should be fixed.

global_logger = initlogging(int(0), __name__)
global_logger.debug("Started logger")


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


blockchain = connect_to_blockchain_daemon()

if __name__ == "__main__":
    mnd = MasterNodeDaemon()
    mnd.run_event_loop()
