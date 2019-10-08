from core_modules.http_rpc import RPCClient


def get_rpc_client_for_masternode(masternode):
    remote_pastelid = masternode['extKey']
    ip, py_rpc_port = masternode['extAddress'].split(':')
    rpc_client = RPCClient(remote_pastelid, ip, py_rpc_port)
    return rpc_client

