import os
import time
import bitcoinrpc
from core_modules.blockchain import BlockChain
from core_modules.logger import initlogging
from core_modules.settings import Settings

global_logger = initlogging(int(0), __name__, Settings.LOG_LEVEL)

#  global blockchain connection object, used for cNode communication
_blockchain = None


def connect_to_blockchain_daemon():
    pastelid = os.environ.get('PASTEL_ID')
    passphrase = os.environ.get('PASSPHRASE')

    while True:
        if pastelid and passphrase:  # running a wallet
            blockchain = BlockChain(Settings.CNODE_RPC_USER, Settings.CNODE_RPC_PWD,
                                    Settings.CNODE_RPC_IP, Settings.CNODE_RPC_PORT,
                                    pastelid=pastelid, passphrase=passphrase)
        else:  # running a node
            blockchain = BlockChain(Settings.CNODE_RPC_USER, Settings.CNODE_RPC_PWD,
                                    Settings.CNODE_RPC_IP, Settings.CNODE_RPC_PORT)

        try:
            blockchain.getwalletinfo()
        except (ConnectionRefusedError, bitcoinrpc.authproxy.JSONRPCException) as exc:
            global_logger.debug("Exception %s while getting wallet info, retrying..." % exc)
            time.sleep(0.5)
        else:
            global_logger.debug("Successfully connected to daemon!")
            break
    return blockchain


# blockchain connection lazy initializer
def get_blockchain_connection():
    global _blockchain
    if not _blockchain:
        _blockchain = connect_to_blockchain_daemon()
    return _blockchain


basedir = os.getcwd()


def reset_blockchain_connection():
    global _blockchain
    _blockchain = None
