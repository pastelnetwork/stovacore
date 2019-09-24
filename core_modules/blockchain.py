import time

from http.client import CannotSendRequest, RemoteDisconnected
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

from core_modules.blackbox_modules.blockchain import store_data_in_utxo, \
    retrieve_data_from_utxo
from core_modules.settings import NetWorkSettings
from core_modules.logger import initlogging


class NotEnoughConfirmations(Exception):
    pass


DEFAULT_PASTEL_ID_PASSPHRASE = 'putvalidpassphrasehereorreplacewithenvvar'


class BlockChain:
    def __init__(self, user, password, ip, rpcport, pastelid=None, passphrase=None):
        self.url = "http://%s:%s@%s:%s" % (user, password, ip, rpcport)
        self.__reconnect()
        self.__logger = initlogging('', __name__)

        # for masternode mode - pastelID should be empty and fetched automatically
        # for wallet API mode - user will change which pastelID use, so wallet_api will create Blockchain object with
        # predefined pastelid
        if not pastelid:
            self.pastelid = self.get_or_create_pastel_id()
        else:
            self.pastelid = pastelid

        # passing `passphrase` parameter has the same idea as `pastelid` one.
        # we pass it for wallet_api and leave blank for masternode
        if not passphrase:
            self.passphrase = DEFAULT_PASTEL_ID_PASSPHRASE
        else:
            self.passphrase = passphrase

    def get_or_create_pastel_id(self):
        pastelid_list = self.pastelid_list()

        if not len(pastelid_list):
            result = self.pastelid_newkey(self.passphrase)
            return result['pastelid']
        else:
            return pastelid_list[0]['PastelID']

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
            except (BrokenPipeError, CannotSendRequest, RemoteDisconnected) as exc:
                print("RECONNECTING %s" % exc)
                self.__reconnect()
            else:
                break
        return ret

    def help(self):
        return self.__call_jsonrpc("help")

    def addnode(self, node, mode):
        return self.__call_jsonrpc("addnode", node, mode)

    def getlocalfee(self):
        return self.__call_jsonrpc("masternode", "getlocalfee")

    def getnetworkfee(self):
        return self.__call_jsonrpc("masternode", "getnetworkfee")

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

    def pastelid_list(self):
        # response example:
        # [{'PastelID': 'jXZghafefxPUfkWesi4qUKrpkPfAsG9QiGDBYUcdTxuyg1XpwbZrzYQrjdJSLPwL8BGGdriLk3azkBiMcSHhw6'}]
        return self.__call_jsonrpc("pastelid", "list")

    def pastelid_newkey(self, passphrase):
        return self.__call_jsonrpc("pastelid", "newkey", passphrase)

    def search_chain(self, confirmations=NetWorkSettings.REQUIRED_CONFIRMATIONS):
        blockcount = self.getblockcount() - 1
        for blocknum in range(1, blockcount + 1):
            for txid in self.get_txids_for_block(blocknum, confirmations=confirmations):
                yield txid

    def pastelid_sign(self, base64data):
        return self.__call_jsonrpc("pastelid", "sign", base64data, self.pastelid, self.passphrase)

    def pastelid_verify(self, base64data, signature):
        return self.__call_jsonrpc("pastelid", "verify", base64data, signature, self.pastelid)

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
