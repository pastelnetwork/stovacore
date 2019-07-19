import asyncio
import time

from http.client import CannotSendRequest
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

from core_modules.blackbox_modules.blockchain import store_data_in_utxo, \
    retrieve_data_from_utxo
from core_modules.settings import NetWorkSettings
from core_modules.logger import initlogging


# TODO: type check all these rpc calls, so that we can rely on it better

class NotEnoughConfirmations(Exception):
    pass


class BlockChain:
    def __init__(self, user, password, ip, rpcport):
        self.url = "http://%s:%s@%s:%s" % (user, password, ip, rpcport)
        self.__reconnect()
        self.__logger = initlogging('', __name__)

    def __reconnect(self):
        while True:
            try:
                newjsonrpc = AuthServiceProxy(self.url)

                # we need this so that we know the blockchain has started
                newjsonrpc.getwalletinfo()
            except ConnectionRefusedError:
                time.sleep(0.1)
            except JSONRPCException as exc:
                if exc.code == -28:
                    time.sleep(0.1)
                else:
                    raise
            else:
                self.__jsonrpc = newjsonrpc
                break

    def __call_jsonrpc(self, name, *params):
        while True:
            f = getattr(self.__jsonrpc, name)
            try:
                if len(params) == 0:
                    ret = f()
                else:
                    ret = f(*params)
            except (BrokenPipeError, CannotSendRequest) as exc:
                print("RECONNECTING %s" % exc)
                self.__reconnect()
            else:
                break
        return ret

    def help(self):
        return self.__call_jsonrpc("help")

    def addnode(self, node, mode):
        return self.__call_jsonrpc("addnode", node, mode)

    def listunspent(self, minimum=1, maximum=9999999, addresses=[]):
        return self.__call_jsonrpc("listunspent", minimum, maximum, addresses)

    def getblockchaininfo(self):
        return self.__call_jsonrpc("getblockchaininfo")

    def getmempoolinfo(self):
        return self.__call_jsonrpc("getmempoolinfo")

    def gettxoutsetinfo(self):
        return self.__call_jsonrpc("gettxoutsetinfo")

    def getmininginfo(self):
        return self.__call_jsonrpc("getmininginfo")

    def getnetworkinfo(self):
        return self.__call_jsonrpc("getnetworkinfo")

    def getpeerinfo(self):
        return self.__call_jsonrpc("getpeerinfo")

    def getwalletinfo(self):
        return self.__call_jsonrpc("getwalletinfo")

    def getbalance(self):
        return self.__call_jsonrpc("getbalance")

    def getnewaddress(self):
        return self.__call_jsonrpc("getnewaddress")

    def createrawtransaction(self, transactions, addresses):
        return self.__call_jsonrpc("createrawtransaction", transactions, addresses)

    def decoderawtransaction(self, transaction_hex):
        return self.__call_jsonrpc("decoderawtransaction", transaction_hex)

    def signrawtransaction(self, transaction_hex):
        return self.__call_jsonrpc("signrawtransaction", transaction_hex)

    def fundrawtransaction(self):
        return self.__call_jsonrpc("fundrawtransaction")

    def sendtoaddress(self, address, amount, private_comment="", public_comment=""):
        return self.__call_jsonrpc("sendtoaddress", address, amount, private_comment, public_comment)

    def sendrawtransaction(self, transaction_hex):
        return self.__call_jsonrpc("sendrawtransaction", transaction_hex)

    def getblock(self, blocknum):
        return self.__call_jsonrpc("getblock", blocknum)

    def getblockcount(self):
        return int(self.__call_jsonrpc("getblockcount"))

    def getaccountaddress(self, address):
        return self.__call_jsonrpc("getaccountaddress", address)

    def mnsync(self, param):
        return self.__call_jsonrpc("mnsync", param)

    def gettransaction(self, txid):
        return self.__call_jsonrpc("gettransaction", txid)

    def listsinceblock(self):
        return self.__call_jsonrpc("listsinceblock")

    def getbestblockhash(self):
        return self.__call_jsonrpc("getbestblockhash")

    def getrawtransaction(self, txid, verbose):
        return self.__call_jsonrpc("getrawtransaction", txid, verbose)

    def getrawmempool(self, verbose):
        return self.__call_jsonrpc("getrawmempool", verbose)

    def generate(self, n):
        return self.__call_jsonrpc("generate", int(n))

    def masternode_workers(self, blocknum=None):
        if blocknum is None:
            result = self.__call_jsonrpc("masternode", "workers")
        else:
            result = self.__call_jsonrpc("masternode", "workers", str(blocknum))
        # cNode returns data with the following format:
        # {<block_number>: [{node_data1, node_data2, node_data3}]}
        return list(result.values())[0]
        # return [{
        #     "mnAddress": "18.224.19.143:19933",
        #     "mnPrivKey": "922s2UewLSPFKfbU59RR3h4d7sRvK2SENGn9wfavKniXPE9t5UN",
        #     "outIndex": "1",
        #     "pyAddress": "18.224.19.143:4444",
        #     "pyCfg": None,
        #     "pyPubKey": "xmLR5XkvzsSIA+3q6nVSpOjuNoILvt2v+JJNNRccdUI3cA0Z1GId5SQ7zfN1Y5LNjkaPUKaoHFO/yDxXEg2YfxaA",
        #     "txid": "a97dcbecdeb237f6055ea0ef7325d449e71756227deb1a90b0f1697efac066b7"
        # },
        #     {
        #         "mnAddress": "3.16.43.43:19933",
        #         "mnPrivKey": "92ktJU7mB1umq8nCgXgXFvNoN3Te91HxkhJ9SXz3oJsCcWvMYWS",
        #         "outIndex": "0",
        #         "pyAddress": "3.16.43.43:4444",
        #         "pyCfg": None,
        #         "pyPubKey": "C1cvrlDBd7H5WNUOTH4Dkh1EoCUpov6ronjtUq7kAv4HGf09hBEYxXHXlup7KKvK1q9n0z+tfNeWkCt9UhnPHzsB",
        #         "txid": "5d337a835bb61102e35d8011cfe0707618d02182db3f0213a514257e4f009a33"
        #     },
        #     {
        #         "mnAddress": "18.216.28.255:19933",
        #         "mnPrivKey": "93Fbxfr1FBjYRV1AbbBLEWuc4RS7J1Es3PUYj6g44EoTGE6EEwu",
        #         "outIndex": "1",
        #         "pyAddress": "18.216.28.255:4444",
        #         "pyCfg": None,
        #         "pyPubKey": "H62rxYbqmNyW+C+TdjfmsTwlDa3/wEfvNjaiScw2Hu5brlgR3ZvmjdSGwg7pDZJQYOCEGRfHYGS4Iye/bF+blywB",
        #         "txid": "73130f53545e465eacb705b9425439b3c23b45a9b0084c7ec1deb0c9d1225be8"
        #     }
        # ]

    def search_chain(self, confirmations=NetWorkSettings.REQUIRED_CONFIRMATIONS):
        blockcount = self.getblockcount() - 1
        for blocknum in range(1, blockcount + 1):
            for txid in self.get_txids_for_block(blocknum, confirmations=confirmations):
                yield txid

    def get_txids_for_block(self, blocknum, confirmations):
        try:
            block = self.getblock(str(blocknum))
        except JSONRPCException as exc:
            if exc.code == -8:
                # Block height out of range
                raise NotEnoughConfirmations
            else:
                raise

        if block["confirmations"] < confirmations:
            raise NotEnoughConfirmations
        else:
            for txid in block["tx"]:
                yield txid

    def store_data_in_utxo(self, input_data):
        while True:
            try:
                txid = store_data_in_utxo(self.__jsonrpc, input_data)
            except BrokenPipeError:
                self.__reconnect()
            else:
                break
        return txid

    def retrieve_data_from_utxo(self, blockchain_transaction_id):
        while True:
            try:
                return retrieve_data_from_utxo(self.__jsonrpc, blockchain_transaction_id)
            except BrokenPipeError:
                self.__reconnect()
