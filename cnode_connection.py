import os
import time
import bitcoinrpc
from core_modules.blockchain import BlockChain
from core_modules.logger import initlogging

global_logger = initlogging(int(0), __name__)

#  global blockchain connection object, used for cNode communication
_blockchain = None


def connect_to_blockchain_daemon():
    pastelid = os.environ.get('PASTEL_ID')
    passphrase = os.environ.get('PASSPHRASE')

    while True:
        if pastelid and passphrase:  # running a wallet
            blockchain = BlockChain(user='rt',
                                    password='rt',
                                    ip='127.0.0.1',
                                    rpcport=19932,
                                    pastelid=pastelid,
                                    passphrase=passphrase
                                    )
        else:  # running a node
            blockchain = BlockChain(user='rt',
                                    password='rt',
                                    ip='127.0.0.1',
                                    rpcport=19932
                                    )

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
