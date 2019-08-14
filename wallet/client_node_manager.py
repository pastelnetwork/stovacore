import base64
import wallet.settings as settings
from core_modules.http_rpc import RPCClient
from core_modules.helpers import get_nodeid_from_pubkey
from core_modules.logger import initlogging
from debug.masternode_conf import MASTERNODES

class ClientNodeManager:
    def __init__(self, privkey, pubkey, blockchain):
        self.__logger = initlogging('ClientNodeManager', __name__)
        self.__privkey = privkey
        self.__pubkey = pubkey
        self.__blockchain = blockchain

    def get_masternode_ordering(self, blocknum=None):
        if settings.DEBUG:
            workers = [MASTERNODES['mn4'], MASTERNODES['mn3'], MASTERNODES['mn2']]
        else:
            workers = self.__blockchain.masternode_workers(blocknum)
        mn_rpc_clients = []

        for node in workers:
            py_pub_key = node['extKey']
            pubkey = base64.b64decode(py_pub_key)

            node_id = get_nodeid_from_pubkey(pubkey)
            ip, py_rpc_port = node['extAddress'].split(':')
            rpc_client = RPCClient(self.__privkey, self.__pubkey,
                                   node_id, ip, py_rpc_port, pubkey)
            mn_rpc_clients.append(rpc_client)
        return mn_rpc_clients

    def get_rpc_client_for_masternode(self, masternode):
        py_pub_key = masternode['extAddress']
        pubkey = base64.b64decode(py_pub_key)

        node_id = get_nodeid_from_pubkey(pubkey)
        ip, py_rpc_port = masternode['extAddress'].split(':')
        rpc_client = RPCClient(self.__privkey, self.__pubkey,
                               node_id, ip, py_rpc_port, pubkey)
        return rpc_client
