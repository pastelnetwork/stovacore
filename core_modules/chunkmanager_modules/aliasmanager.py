from core_modules.helpers import get_pynode_digest_int
from core_modules.settings import NetWorkSettings
from core_modules.logger import initlogging
from cnode_connection import get_blockchain_connection
from utils.mn_rpc import get_rpc_client_for_masternode


class AliasManager:
    """
    This purpose of this class is:
     - Maintain actual masternode list (using task which periodically will execute cNode's `masternode list` command,
     compare data with what we currently have in our DB and update it accordingly.
     - Masternode ID is pastelID. We use it to calculate `XOR distance` between entities (mostly, between a masternode
     and a chunk). This class should go though live of known chunks in out DB, and calculate chunk owner by calculating
     XOR distance between each chunk and masternode. As Cartesian product of all masternodes * all chunks is quite a huge
     number of combinations - we should calculate distance in two cases:
       1. Masternode has been added (need to calculate XOR distance from new MN to every chunk), expected to be a large
       number of rows affected.
       2. Chunk has been added (calculate distance from this chunk to every MN), expected to affect small number of
       rows.
     Also, after each recalculation we chunk should we keep (according to the whitepaper, top 10 masternodes closest to
     this chunk is terms of XOR distance should store the chunk). Reflected in LUBY_REDUNDANCY_FACTOR NetworkSetting.
     Thus, it will be another periodic task.
     - In this way, with the help of AliasManager we always can answer 2 simple but important questions:
      1. Which MN should we request for a given chunk
      2. Which chunk are we expected to store.
    """
    def __init__(self):
        self.__logger = initlogging('', __name__)

        # helper lookup table for alias generation and other nodes
        aliases = []
        for i in range(NetWorkSettings.REPLICATION_FACTOR):
            digest_int = get_pynode_digest_int(i.to_bytes(1, byteorder='big') + NetWorkSettings.ALIAS_SEED)
            # self.__logger.debug("Alias digest %s -> %s" % (i, chunkid_to_hex(digest_int)))
            aliases.append(digest_int)

        self.__alias_digests = tuple(aliases)

    def __find_owners_for_chunk(self, chunkid):
        mns = get_blockchain_connection().masternode_list().values()
        mns_rpc_clients = [get_rpc_client_for_masternode(mn) for mn in mns]
        owners = [mns_rpc_clients[0]]  # FIXME: owner is locked only for testing
        # for alias_digest in self.__alias_digests:
        #     # compute alt_key
        #     alt_key = alias_digest ^ chunkid
        #
        #     # check if we have an MasterNodes
        #     if len(mn_nodeids) == 0:
        #         raise RuntimeError("There are no MNs online!")
        #
        #     # found owners for this alt_key
        #     owner, min_distance = None, None
        #     for nodeid in mn_nodeids:
        #         distance = alt_key ^ nodeid
        #         if owner is None or distance < min_distance:
        #             owner = nodeid
        #             min_distance = distance
        #     owners.add(owner)
        return owners

    def find_other_owners_for_chunk(self, chunkid):
        owners = self.__find_owners_for_chunk(chunkid)
        # return owners - {get_blockchain_connection().pastelid}
        return owners

    def we_own_chunk(self, chunkid):
        return get_blockchain_connection().pastelid in self.__find_owners_for_chunk(chunkid)
