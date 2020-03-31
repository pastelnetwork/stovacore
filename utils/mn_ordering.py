from core_modules.rpc_client import RPCClient
from cnode_connection import get_blockchain_connection


def get_masternode_ordering(blocknum=None):
    """
    Fetch `masternode workers` from cNode, create RPCClient for each one,
    return list of RPCClients.
    """
    mn_rpc_clients = []
    workers = get_blockchain_connection().masternode_top(blocknum)
    index = 0
    while len(mn_rpc_clients) < 3:
        node = workers[index]
        index += 1
        if index >= len(workers):
            raise ValueError('There are less then 3 valid masternodes in `masternode top` output. '
                             'Cannot select a quorum of 3 MNs.')
        remote_pastelid = node['extKey']
        ip, py_rpc_port = node['extAddress'].split(':')
        if not node['extKey'] or not ip or not py_rpc_port:
            continue
        rpc_client = RPCClient(remote_pastelid, ip, py_rpc_port)
        mn_rpc_clients.append(rpc_client)
    return mn_rpc_clients
