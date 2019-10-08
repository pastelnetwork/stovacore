import wallet.settings as settings
from cnode_connection import blockchain
from core_modules.http_rpc import RPCClient
from core_modules.logger import initlogging
from debug.masternode_conf import MASTERNODES


class ClientNodeManager:
    def __init__(self):
        self.__logger = initlogging('ClientNodeManager', __name__)

    def get_masternode_ordering(self, blocknum=None):
        if settings.DEBUG:
            workers = [MASTERNODES['mn4'], MASTERNODES['mn3'], MASTERNODES['mn2']]
        else:
            workers = blockchain.masternode_workers(blocknum)
        mn_rpc_clients = []

        for node in workers:
            remote_pastelid = node['extKey']

            ip, py_rpc_port = node['extAddress'].split(':')
            rpc_client = RPCClient(remote_pastelid, ip, py_rpc_port)
            mn_rpc_clients.append(rpc_client)
        return mn_rpc_clients
