import base64

from core_modules.helpers import get_nodeid_from_pubkey
from core_modules.http_rpc import RPCClient
from start_single_masternode import blockchain


def get_masternode_ordering(blocknum, pastel_privkey, pastel_pubkey):
    mn_rpc_clients = []
    workers = blockchain.masternode_workers(blocknum)
    for node in workers:
        py_pub_key = node['extKey']
        pubkey = base64.b64decode(py_pub_key)

        node_id = get_nodeid_from_pubkey(pubkey)
        ip, py_rpc_port = node['extAddress'].split(':')
        rpc_client = RPCClient(pastel_privkey, pastel_pubkey,
                               node_id, ip, py_rpc_port, pubkey)
        mn_rpc_clients.append(rpc_client)
    return mn_rpc_clients
