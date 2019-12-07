import json

import time

from http.client import CannotSendRequest, RemoteDisconnected
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

from core_modules.settings import NetWorkSettings
from core_modules.logger import initlogging


class NotEnoughConfirmations(Exception):
    pass


DEFAULT_PASTEL_ID_PASSPHRASE = 'putvalidpassphrasehereorreplacewithenvvar'


def update_masternode_conf(pastelid):
    import json
    with open('/home/animecoinuser/.pastel/testnet3/masternode.conf', 'r') as f:
        config_data = f.read()
    json_config_data = json.loads(config_data)

    mn_key = list(json_config_data.keys())[0]
    if json_config_data[mn_key]['extPubKey'] == pastelid:
        return
    json_config_data[mn_key]['extPubKey'] = pastelid
    final_data = json.dumps(json_config_data, indent=4, sort_keys=True)
    with open('/home/animecoinuser/.pastel/testnet3/masternode.conf', 'w') as f:
        f.write(final_data)


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
            self.pastelid = self.get_or_create_pastel_id()
            update_masternode_conf(self.pastelid)
        else:
            self.pastelid = pastelid

    def get_or_create_pastel_id(self):
        # FIXME: when fetching list of pastelID need to check `registered` or `status` flag if
        #  the given pastelid is registered
        #  if not - register.
        pastelid_list = self.pastelid_list()

        if not len(pastelid_list):
            result = self.pastelid_newkey(self.passphrase)
            response = self.mnid_register(result['pastelid'], self.passphrase)
            self.__logger.warn('Registered mnid {}, txid: {}'.format(result['pastelid'], response['txid']))
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

    def masternode_list(self):
        # return self.__call_jsonrpc("masternode", "list", "extra")
        # FIXME: only for testing, to limit set of masternodes
        return {
            'mn4': {
                'extKey': 'jXZVtBmehoxYPotVrLdByFNNcB8jsryXhFPgqRa95i2x1mknbzSef1oGjnzfiwRtzReimfugvg41VtA7qGfDZR',
                'extAddress': '18.216.28.255:4444'
            },
            'mn5': {
                'extKey': 'jXY39ehN4BWWpXLt4Q2zpcmypSAN9saWCweGRtJTxK87ktftjigfJwE6X9JoVfBduDjzEG4uBVR8Es6jVFMAbW',
                'extAddress': '18.191.111.96:4444'
            },
            'mn6': {
                'extKey': 'jXa2jiukvPktEdPvGo5nCLaMHxFRLneXMUNLGU4AUkuMmFq6ADerSJZg3Htd7rGjZo6HM92CgUFW1LjEwrKubd',
                'extAddress': '18.222.118.140:4444'
            }
        }

    def masternode_top(self, blocknum=None):
        if blocknum is None:
            result = self.__call_jsonrpc("masternode", "top")
        else:
            result = self.__call_jsonrpc("masternode", "top", blocknum)
        # cNode returns data with the following format:
        # {<block_number>: [{node_data1, node_data2, node_data3}]}
        # return list(result.values())[0]
        return [
            # mn4
            {
                "rank": "1",
                "IP:port": "18.216.28.255:19933",
                "protocol": 170007,
                "outpoint": "73130f53545e465eacb705b9425439b3c23b45a9b0084c7ec1deb0c9d1225be8-1",
                "payee": "tPpMnvVmA4Lbab4JHtXmK9Jt9ZFxEgN1Rmj",
                "lastseen": 1569486643,
                "activeseconds": 7837959,
                "extAddress": "18.216.28.255:4444",
                "extKey": "jXZWTjviQnvqMx39H4AgTYm4bswEfR79UYgccJtDq4D5qXshStEypFNcPQhGbf46pQWkURuHFvtiTFUCu7GdSa",
                "extCfg": ""
            },
            # mn5
            {
                "rank": "2",
                "IP:port": "18.191.111.96:19933",
                "protocol": 170007,
                "outpoint": "055b2e9833690e44c62e9c854fe33a770ac427647079ef571a95a3b8a24887fd-0",
                "payee": "tPgYbXJNTMDjxaZnwgKVtcJ2ZKgdf9WDcZE",
                "lastseen": 1569486926,
                "activeseconds": 7838259,
                "extAddress": "18.191.111.96:4444",
                "extKey": "jXZDyqqMDXSz1ycBLCZJ82U2GCSL7m8KTet3i685pFroMdjGaPvdCmVZWrkxoKn1H7wSHibVEohHV7u5juDrne",
                "extCfg": ""
            },
            # mn6
            {
                "rank": "3",
                "IP:port": "18.222.118.140:19933",
                "protocol": 170007,
                "outpoint": "f900925fe119af0438641b10945b9377eb52e06fe108e785fccd3dcd6d8384f4-1",
                "payee": "tPRcrQ5P4vm3yKFgy3y1Rs3MaYcdVvEsw57",
                "lastseen": 1569486686,
                "activeseconds": 7837992,
                "extAddress": "18.222.118.140:4444",
                "extKey": "jXZpYBdkMuN9zpCj8BJjTFF1RV54824WstxS816GgM2V1myd5EzwnGmREG1zzbLGWf2syYhFoYhg7gjdd2mkoE",
                "extCfg": ""
            }
        ]

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

    def search_chain(self, confirmations=NetWorkSettings.REQUIRED_CONFIRMATIONS):
        blockcount = self.getblockcount() - 1
        for blocknum in range(1, blockcount + 1):
            for txid in self.get_txids_for_block(blocknum, confirmations=confirmations):
                yield txid

    def pastelid_sign(self, base64data):
        response = self.__call_jsonrpc("pastelid", "sign", base64data, self.pastelid, self.passphrase)
        return response['signature']

    def pastelid_verify(self, base64data, signature, pasteid_to_verify):
        return self.__call_jsonrpc("pastelid", "verify", base64data, signature, pasteid_to_verify)

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
