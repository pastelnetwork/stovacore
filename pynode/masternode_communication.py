import base64
import random

from core_modules.http_rpc import RPCClient
from core_modules.helpers import get_nodeid_from_pubkey
from core_modules.logger import initlogging
from cnode_connection import blockchain


class NodeManager:
    def __init__(self, nodenum):
        self.__masternodes = {}
        self.__nodenum = nodenum
        self.__logger = initlogging('', __name__)

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
        workers = blockchain.masternode_workers(blocknum)
        for node in workers:
            remote_pastelid = node['extKey']

            ip, py_rpc_port = node['extAddress'].split(':')
            rpc_client = RPCClient(remote_pastelid, ip, py_rpc_port)
            mn_rpc_clients.append(rpc_client)
        return mn_rpc_clients

    def get_rpc_client_for_masternode(self, masternode):
        remote_pastelid = masternode['extKey']
        ip, py_rpc_port = masternode['extAddress'].split(':')
        rpc_client = RPCClient(remote_pastelid, ip, py_rpc_port)
        return rpc_client

    def update_masternode_list(self):
        workers_list = blockchain.masternode_workers()

        # parse new list
        new_mn_list = {}
        for node in workers_list:
            # extKey is pastelID of the remote node
            remote_pastelid = node['extKey']
            if not remote_pastelid:
                continue
            ip, py_rpc_port = node['extAddress'].split(':')
            new_mn_list[remote_pastelid] = RPCClient(remote_pastelid, ip, py_rpc_port)

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
