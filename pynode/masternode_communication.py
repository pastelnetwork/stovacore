import base64
import random

from core_modules.http_rpc import RPCClient
from core_modules.helpers import get_nodeid_from_pubkey
from core_modules.logger import initlogging


class NodeManager:
    def __init__(self, nodenum, privkey, pubkey, blockchain):
        self.__masternodes = {}
        self.__nodenum = nodenum
        self.__logger = initlogging('', __name__)
        self.__privkey = privkey
        self.__pubkey = pubkey
        self.__blockchain = blockchain

    def get(self, nodeid):
        return self.__masternodes[nodeid]

    def get_all(self):
        return tuple(self.__masternodes.values())

    def get_random(self):
        try:
            sample = random.sample(self.get_all(), 1)
        except ValueError:
            return None
        return sample[0]

    def get_other_nodes(self, mynodeid):
        other_nodes = []
        for mn in self.__masternodes.values():
            if mn.nodeid != mynodeid:
                other_nodes.append(mn.nodeid)
        return other_nodes

    def get_masternode_ordering(self, blocknum):
        mn_rpc_clients = []
        workers = self.__blockchain.masternode_workers(blocknum)
        for node in workers:
            py_pub_key = node['pyPubKey']
            pubkey = base64.b64decode(py_pub_key)

            node_id = get_nodeid_from_pubkey(pubkey)
            ip, py_rpc_port = node['pyAddress'].split(':')
            rpc_client = RPCClient(self.__nodenum, self.__privkey, self.__pubkey,
                                   node_id, ip, py_rpc_port, pubkey)
            mn_rpc_clients.append(rpc_client)
        return mn_rpc_clients

    def get_rpc_client_for_masternode(self, masternode):
        py_pub_key = masternode['pyPubKey']
        pubkey = base64.b64decode(py_pub_key)

        node_id = get_nodeid_from_pubkey(pubkey)
        ip, py_rpc_port = masternode['pyAddress'].split(':')
        rpc_client = RPCClient(self.__nodenum, self.__privkey, self.__pubkey,
                               node_id, ip, py_rpc_port, pubkey)
        return rpc_client

    def update_masternode_list(self):
        workers_list = self.__blockchain.masternode_workers()

        # parse new list
        new_mn_list = {}
        for node in workers_list:
            py_pub_key = node['pyPubKey']
            pubkey = base64.b64decode(py_pub_key)
            if not pubkey:
                continue
            ip, py_rpc_port = node['pyAddress'].split(':')
            node_id = get_nodeid_from_pubkey(pubkey)
            new_mn_list[node_id] = RPCClient(self.__nodenum, self.__privkey, self.__pubkey,
                                             node_id, ip, py_rpc_port, pubkey)

        old = set(self.__masternodes.keys())
        new = set(new_mn_list.keys())
        added = new - old
        removed = old - new

        for i in added:
            self.__logger.debug("Added MN %s" % i)
        for i in removed:
            self.__logger.debug("Removed MN %s" % i)

        self.__masternodes = new_mn_list
        return added, removed
