import asyncio
import requests

from aiohttp import ClientSession

from core_modules.logger import initlogging
from core_modules.rpc_serialization import pack_and_sign, verify_and_unpack
from core_modules.helpers import chunkid_to_hex


class RPCException(Exception):
    pass


class RPCClient:
    def __init__(self, remote_pastelid, server_ip, server_port):
        self.__logger = initlogging('', __name__, level="debug")

        # variables of the server (the MN)
        self.__server_ip = server_ip
        self.server_ip = server_ip
        self.__server_port = server_port
        self.remote_pastelid = remote_pastelid

        self.__name = ''
        self.__reputation = None

    def __str__(self):
        return 'RPC Client for node with pastelID: {}'.format(self.remote_pastelid)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __return_rpc_packet(self, sender_id, msg):
        response_packet = pack_and_sign(sender_id, msg)
        return response_packet

    async def __send_rpc_and_wait_for_response(self, msg):
        url = 'https://{}:{}/'.format(self.__server_ip, self.__server_port)
        async with ClientSession() as session:
            async with session.post(url, data=msg, ssl=False) as resp:
                msg = await resp.read()
                return msg

    def __send_rpc_and_wait_for_response_sync(self, msg):
        url = 'https://{}:{}/'.format(self.__server_ip, self.__server_port)
        resp = requests.post(url, data=msg, verify=False)
        self.__logger.info('Returned status code {}'.format(resp.status_code))
        return resp.content

    async def __send_rpc_to_mn(self, response_name, request_packet):
        node_name = self.__name if self.__name else self.__server_ip
        await asyncio.sleep(0)
        msg = 'Sending RPC message to {}'.format(node_name)
        self.__logger.info(msg)

        response_packet = await self.__send_rpc_and_wait_for_response(request_packet)

        sender_id, response_msg = verify_and_unpack(response_packet)
        rpcname, success, response_data = response_msg
        self.__logger.info('RPC {} from {} success: {}, data: {}'.format(rpcname, node_name, success, response_data))

        if rpcname != response_name:
            raise ValueError("Spotcheck response has rpc name: %s" % rpcname)

        if success != "SUCCESS":
            self.__logger.warn('Error from masternode {}'.format(node_name))
            raise RPCException(response_data)

        return response_data

    def __send_rpc_to_mn_sync(self, response_name, request_packet):
        node_name = self.__name if self.__name else self.__server_ip
        msg = 'Sending RPC message to {}'.format(node_name)
        self.__logger.info(msg)

        response_packet = self.__send_rpc_and_wait_for_response_sync(request_packet)

        sender_id, response_msg = verify_and_unpack(response_packet)
        rpcname, success, response_data = response_msg
        self.__logger.info('RPC {} from {} success: {}, data: {}'.format(rpcname, node_name, success, response_data))

        if rpcname != response_name:
            raise ValueError("Spotcheck response has rpc name: %s" % rpcname)

        if success != "SUCCESS":
            self.__logger.warn('Error from masternode {}'.format(node_name))
            raise RPCException(response_data)

        return response_data

    async def send_rpc_ping(self, data):
        await asyncio.sleep(0)

        request_packet = self.__return_rpc_packet(self.remote_pastelid, ["PING_REQ", data])

        try:
            returned_data = await self.__send_rpc_to_mn("PING_RESP", request_packet)
        except Exception as e:
            self.__logger.warn('Skipping by timeout')
            raise e
            # return None

        if set(returned_data.keys()) != {"data"}:
            raise ValueError("RPC parameters are wrong for PING RESP: %s" % returned_data.keys())

        if type(returned_data["data"]) != bytes:
            raise TypeError("data is not bytes: %s" % type(returned_data["data"]))

        response_data = returned_data["data"]

        return response_data

    def send_rpc_ping_sync(self, data):

        request_packet = self.__return_rpc_packet(self.remote_pastelid, ["PING_REQ", data])

        try:
            returned_data = self.__send_rpc_to_mn_sync("PING_RESP", request_packet)
        except Exception as e:
            self.__logger.warn('Skipping by timeout')
            raise e
            # return None

        if set(returned_data.keys()) != {"data"}:
            raise ValueError("RPC parameters are wrong for PING RESP: %s" % returned_data.keys())

        if type(returned_data["data"]) != bytes:
            raise TypeError("data is not bytes: %s" % type(returned_data["data"]))

        response_data = returned_data["data"]

        return response_data

    async def send_rpc_fetchchunk(self, chunkid):

        await asyncio.sleep(0)

        self.__logger.info("FETCHCHUNK REQUEST to {} ({})".format(self.__name, self.server_ip))
        self.__logger.debug("FETCHCHUNK REQUEST to {}, chunkid: {}".format(self, chunkid_to_hex(int(chunkid))))

        # chunkid is bignum so we need to serialize it
        chunkid_str = chunkid_to_hex(int(chunkid))
        request_packet = self.__return_rpc_packet(self.remote_pastelid, ["FETCHCHUNK_REQ", {"chunkid": chunkid_str}])

        response_data = await self.__send_rpc_to_mn("FETCHCHUNK_RESP", request_packet)

        if set(response_data.keys()) != {"chunk"}:
            raise ValueError("RPC parameters are wrong for FETCHCHUNK_RESP: %s" % response_data.keys())

        if type(response_data["chunk"]) not in [bytes, type(None)]:
            raise TypeError("chunk is not bytes or None: %s" % type(response_data["chunk"]))

        chunk_data = response_data["chunk"]

        return chunk_data

    async def __send_mn_ticket_rpc(self, rpcreq, rpcresp, data):
        await asyncio.sleep(0)
        request_packet = self.__return_rpc_packet(self.remote_pastelid, [rpcreq, data])
        returned_data = await self.__send_rpc_to_mn(rpcresp, request_packet)
        return returned_data

    async def call_masternode(self, req, resp, data):
        return await self.__send_mn_ticket_rpc(req, resp, data)
