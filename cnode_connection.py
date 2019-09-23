import os
import time
import bitcoinrpc
from core_modules.blockchain import BlockChain
from core_modules.logger import initlogging


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


# blockchain aka cNode aka pasteld connection object.
# it has `pastelid` attribute - current pastelID
blockchain = connect_to_blockchain_daemon()

basedir = os.getcwd()
