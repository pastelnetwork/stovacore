import random

from core_modules.database import Masternode
from core_modules.logger import initlogging
from cnode_connection import blockchain


class MasternodeManager:
    def __init__(self):
        self.__masternodes = {}
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

    @classmethod
    def update_masternode_list(cls):
        """
        Fetch current masternode list from cNode (by calling `masternode list extra`) and
        update database Masternode table accordingly.
        Return 2 sets of MN pastelIDs - added and removed,
        """
        masternode_list = blockchain.masternode_list()

        # parse new list
        fresh_mn_list = {}
        for k in masternode_list:
            node = masternode_list[k]
            # generate dict of {pastelid: <ip:port>}
            if node['extKey'] and node['extAddress']:
                fresh_mn_list[node['extKey']] = node['extAddress']

        existing_mn_pastelids = set([mn.pastel_id for mn in Masternode.select()])
        fresh_mn_pastelids = set(fresh_mn_list.keys())
        added_pastelids = fresh_mn_pastelids - existing_mn_pastelids
        removed_pastelids = existing_mn_pastelids - fresh_mn_pastelids

        Masternode.delete().where(Masternode.pastel_id.in_(removed_pastelids)).execute()
        Masternode.insert(
            [{'pastel_id': pastelid, 'ext_address': fresh_mn_list[pastelid]} for pastelid in added_pastelids]).execute()
        return added_pastelids, removed_pastelids
