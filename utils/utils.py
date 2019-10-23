from core_modules.http_rpc import RPCClient
from cnode_connection import blockchain


def get_masternode_ordering(blocknum=None):
    """
    Fetch `masternode workers` from cNode, create RPCClient for each one,
    return list of RPCClients.
    """
    mn_rpc_clients = []
    workers = blockchain.masternode_workers(blocknum)
    for node in workers:
        remote_pastelid = node['extKey']
        ip, py_rpc_port = node['extAddress'].split(':')
        rpc_client = RPCClient(remote_pastelid, ip, py_rpc_port)
        mn_rpc_clients.append(rpc_client)
    return mn_rpc_clients
