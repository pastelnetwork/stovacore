from core_modules.helpers import get_pynode_digest_int
from core_modules.settings import NetWorkSettings
from core_modules.logger import initlogging


class AliasManager:
    def __init__(self, nodenum, nodeid, mn_manager):
        self.__logger = initlogging(nodenum, __name__)
        self.__nodeid = nodeid
        self.__mn_manager = mn_manager

        # helper lookup table for alias generation and other nodes
        aliases = []
        for i in range(NetWorkSettings.REPLICATION_FACTOR):
            digest_int = get_pynode_digest_int(i.to_bytes(1, byteorder='big') + NetWorkSettings.ALIAS_SEED)
            # self.__logger.debug("Alias digest %s -> %s" % (i, chunkid_to_hex(digest_int)))
            aliases.append(digest_int)

        self.__alias_digests = tuple(aliases)

    def __find_owners_for_chunk(self, chunkid):
        mn_nodeids = tuple(mn.nodeid for mn in self.__mn_manager.get_all())
        owners = set()
        for alias_digest in self.__alias_digests:
            # compute alt_key
            alt_key = alias_digest ^ chunkid

            # check if we have an MasterNodes
            if len(mn_nodeids) == 0:
                raise RuntimeError("There are no MNs online!")

            # found owners for this alt_key
            owner, min_distance = None, None
            for nodeid in mn_nodeids:
                distance = alt_key ^ nodeid
                if owner is None or distance < min_distance:
                    owner = nodeid
                    min_distance = distance
            owners.add(owner)
        return owners

    def find_other_owners_for_chunk(self, chunkid):
        owners = self.__find_owners_for_chunk(chunkid)
        return owners - {self.__nodeid}

    def we_own_chunk(self, chunkid):
        return self.__nodeid in self.__find_owners_for_chunk(chunkid)
