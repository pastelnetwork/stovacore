"""
Connection client for pasteld http API.
"""
import os
import time
import bitcoinrpc
from core_modules.blockchain import BlockChain
from core_modules.logger import get_logger
from core_modules.settings import Settings

cnode_connection_logger = get_logger("cNode Connection")

#  global blockchain connection object, used for cNode communication
_blockchain = None


def connect_to_blockchain_daemon():
    pastelid = os.environ.get('PASTEL_ID')
    passphrase = os.environ.get('PASSPHRASE')

    cnode_connection_logger.debug("Connecting to cNode at %s:%s as %s..." %
                                  (Settings.CNODE_RPC_IP, Settings.CNODE_RPC_PORT, Settings.CNODE_RPC_USER))

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
            cnode_connection_logger.exception("Exception %s while getting wallet info, retrying..." % exc)
            time.sleep(0.5)
        else:
            cnode_connection_logger.debug("Successfully connected to cNode!")
            break
    return blockchain


# blockchain connection lazy initializer
def get_blockchain_connection():
    global _blockchain
    if not _blockchain:
        _blockchain = connect_to_blockchain_daemon()
    return _blockchain


def reset_blockchain_connection():
    global _blockchain
    _blockchain = None
