import base64
import json

import time

from http.client import CannotSendRequest, RemoteDisconnected
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

from core_modules.logger import initlogging


class NotEnoughConfirmations(Exception):
    pass


DEFAULT_PASTEL_ID_PASSPHRASE = 'putvalidpassphrasehereorreplacewithenvvar'


class BlockChain:
    def __init__(self, user, password, ip, rpcport, pastelid=None, passphrase=None):
        self.url = "http://%s:%s@%s:%s" % (user, password, ip, rpcport)
        self.__reconnect()
        self.__logger = initlogging('', __name__)

        # passing `passphrase` parameter has the same idea as `pastelid` one.
        # we pass it for wallet_api and leave blank for masternode
        if not passphrase:
            self.passphrase = DEFAULT_PASTEL_ID_PASSPHRASE
        else:
            self.passphrase = passphrase

        # for masternode mode - pastelID should be empty and fetched automatically
        # for wallet API mode - user will change which pastelID use, so wallet_api will create Blockchain object with
        # predefined pastelid
        if not pastelid:
            self.pastelid = self.get_pastel_id()
        else:
            self.pastelid = pastelid

    def get_pastel_id(self):
        # FIXME: when fetching list of pastelID need to check `registered` or `status` flag if
        #  the given pastelid is registered
        #  if not - register.
        pastelid_list = self.pastelid_list()

        if not len(pastelid_list):
            raise Exception('There is no pastel IDs on this node. Please register one first.')
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
        return self.__call_jsonrpc("storagefee", "getlocalfee")

    def getnetworkfee(self):
        return self.__call_jsonrpc("storagefee", "getnetworkfee")

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

    def list_tickets(self, ticket_type):
        """
        ticket_type - one of (id, art, act, trade, down)
        """
        return self.__call_jsonrpc("tickets", "list", ticket_type)

    def get_ticket(self, txid):
        """
        ticket_type - one of (id, art, act, trade, down)
        """
        return self.__call_jsonrpc("tickets", "get", txid)

    def masternode_list(self):
        return self.__call_jsonrpc("masternode", "list", "extra")

    def masternode_top(self, blocknum=None):
        if blocknum is None:
            result = self.__call_jsonrpc("masternode", "top")
        else:
            result = self.__call_jsonrpc("masternode", "top", blocknum)
        # cNode returns data with the following format:
        # {<block_number>: [{node_data1, node_data2, node_data3}]}
        return list(result.values())[0]

    def pastelid_list(self):
        # response example:
        # [{'PastelID': 'jXZghafefxPUfkWesi4qUKrpkPfAsG9QiGDBYUcdTxuyg1XpwbZrzYQrjdJSLPwL8BGGdriLk3azkBiMcSHhw6'}]
        return self.__call_jsonrpc("pastelid", "list")

    def pastelid_newkey(self, passphrase):
        return self.__call_jsonrpc("pastelid", "newkey", passphrase)

    def mnid_register(self, pastelid, passphrase):
        return self.__call_jsonrpc("tickets", "register", "mnid", pastelid, passphrase)

    def register_art_ticket(self, base64_data, signatures_dict, key1, key2, art_block, fee):
        """
        :param base64_data: Base64 encoded original ticket created by the artist.
        :param signatures_dict: Signatures (base64) and PastelIDs of the author and verifying masternodes (MN2 and MN3)
        as JSON:
            {
                "artist":{"authorsPastelID": "authorsSignature"},
                "mn2":{"mn2PastelID":"mn2Signature"},
                "mn3":{"mn3PastelID":"mn3Signature"}
            }

        :param key1: The first key to search ticket.
        :param key2: The second key to search ticket.
        :param art_block: The block number when the ticket was created by the wallet. (int)
        :param fee: The agreed upon storag fee.
         :return:
        """
        parameters = [base64_data, json.dumps(signatures_dict), self.pastelid, self.passphrase, key1, key2, art_block,
                      fee]
        return self.__call_jsonrpc("tickets", "register", "art", *parameters)

    def pastelid_sign(self, data: bytes) -> str:
        """
        :return: signature
        """
        # convert data to base64, then to decode string
        base64data = base64.b64encode(data).decode()
        try:
            response = self.__call_jsonrpc("pastelid", "sign", base64data, self.pastelid, self.passphrase)
        except Exception as e:
            self.__logger.warning('Probably your passphrase {} is invalid for a current key'.format(self.passphrase))
            raise e
        return response['signature']

    def pastelid_verify(self, data: bytes, signature: str, pastelid_to_verify: str) -> bool:
        """
        :return: Given signature valid/invalid against given data and pastelID.
        """
        base64data = base64.b64encode(data).decode()
        response = self.__call_jsonrpc("pastelid", "verify", base64data, signature, pastelid_to_verify)
        return True if response['verification'] == 'OK' else False
