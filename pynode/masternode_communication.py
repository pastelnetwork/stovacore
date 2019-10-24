import random

from core_modules.database import Masternode
from core_modules.logger import initlogging
from cnode_connection import get_blockchain_connection


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

