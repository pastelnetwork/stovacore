import asyncio
import requests

from aiohttp import ClientSession, ClientTimeout

from core_modules.logger import initlogging
from core_modules.rpc_serialization import RPCMessage
from core_modules.helpers import chunkid_to_hex


class RPCException(Exception):
    pass


class RPCClient:
    def __init__(self, remote_pastelid, server_ip, server_port):
        self.__logger = initlogging('RPC Client', __name__)
        if not remote_pastelid:
            raise ValueError('Remove pastelid cannot be empty')
        if not server_ip:
            raise ValueError('IP address cannot be empty')
        if not server_port:
            raise ValueError('Port cannot be empty')

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

    def generate_packet(self, data):
        """
        :type data: list
        :param data: data to send
        :return: encoded packet
        :rtype: bytes
        """
        if type(data) != list:
            raise ValueError('Data must be a list!')
        rpc_message = RPCMessage(data, self.remote_pastelid)
        return rpc_message.pack()

    async def __send_rpc_and_wait_for_response(self, msg):
        url = 'https://{}:{}/'.format(self.__server_ip, self.__server_port)
        async with ClientSession(timeout=ClientTimeout(connect=10)) as session:
            async with session.post(url, data=msg, ssl=False) as resp:
                msg = await resp.read()
                return msg

    def __send_rpc_and_wait_for_response_sync(self, msg):
        url = 'https://{}:{}/'.format(self.__server_ip, self.__server_port)
        resp = requests.post(url, data=msg, verify=False)
        self.__logger.info('Returned status code {}'.format(resp.status_code))
        return resp.content

    async def __send_rpc_to_mn(self, response_name, request_packet):
        await asyncio.sleep(0)
        self.__logger.info('Sending RPC message to {}'.format(self.__server_ip))

        response_packet = await self.__send_rpc_and_wait_for_response(request_packet)

        try:
            rpc_message = RPCMessage.reconstruct(response_packet)
        except ValueError:
            self.__logger.exception('Something went wrong when reconstructing message')
            return None

        sender_id, response_msg = rpc_message.sender_id, rpc_message.data
        rpcname, success, response_data = response_msg
        # fixme: log data only if it's not very long.
        self.__logger.warn('RPC {} from {} success: {}, data: {}'.format(rpcname,
                                                                         self.__server_ip, success, response_data))

        if rpcname != response_name:
            raise ValueError("Spotcheck response has rpc name: %s" % rpcname)

        if success != "SUCCESS":
            self.__logger.warn('Error from masternode {}'.format(self.__server_ip))
            raise RPCException(response_data)

        return response_data

    def __send_rpc_to_mn_sync(self, response_name, request_packet):
        node_name = self.__name if self.__name else self.__server_ip
        msg = 'Sending RPC message to {}'.format(node_name)
        self.__logger.info(msg)

        response_packet = self.__send_rpc_and_wait_for_response_sync(request_packet)

        rpc_message = RPCMessage.reconstruct(response_packet)
        sender_id, response_msg = rpc_message.sender_id, rpc_message.data
        rpcname, success, response_data = response_msg
        # fixme: log data only if it's not very long
        self.__logger.info('RPC {} from {} success: {}, data: {}'.format(rpcname, node_name, success, response_data))

        if rpcname != response_name:
            raise ValueError("Spotcheck response has rpc name: %s" % rpcname)

        if success != "SUCCESS":
            self.__logger.warn('Error from masternode {}'.format(node_name))
            raise RPCException(response_data)

        return response_data

    async def send_rpc_ping(self, data):
        await asyncio.sleep(0)

        request_packet = self.generate_packet(["PING_REQ", data])

        try:
            returned_data = await self.__send_rpc_to_mn("PING_RESP", request_packet)
        except Exception as e:
            self.__logger.exception('Skipping by timeout')
            raise e
            # return None

        if set(returned_data.keys()) != {"data"}:
            raise ValueError("RPC parameters are wrong for PING RESP: %s" % returned_data.keys())

        if type(returned_data["data"]) != bytes:
            raise TypeError("data is not bytes: %s" % type(returned_data["data"]))

        response_data = returned_data["data"]

        return response_data

    def send_rpc_ping_sync(self, data):

        request_packet = self.generate_packet(["PING_REQ", data])

        try:
            returned_data = self.__send_rpc_to_mn_sync("PING_RESP", request_packet)
        except Exception as e:
            self.__logger.exception('Skipping by timeout')
            raise e
            # return None

        if set(returned_data.keys()) != {"data"}:
            raise ValueError("RPC parameters are wrong for PING RESP: %s" % returned_data.keys())

        if type(returned_data["data"]) != bytes:
            raise TypeError("data is not bytes: %s" % type(returned_data["data"]))

        response_data = returned_data["data"]

        return response_data

    def send_rpc_execute_sql(self, sql):
        """
        Debugging interface to send atritrary SQL to the masternode and get result back.
        """

        request_packet = self.generate_packet(["SQL_REQ", sql])

        try:
            returned_data = self.__send_rpc_to_mn_sync("SQL_RESP", request_packet)
        except Exception as e:
            self.__logger.exception('Skipping by timeout')
            raise e

        return returned_data["result"]

    async def send_rpc_fetchchunk(self, chunkid):

        await asyncio.sleep(0)

        self.__logger.warn("FETCHCHUNK REQUEST to {} ({})".format(self.__name, self.server_ip))
        self.__logger.warn("FETCHCHUNK REQUEST to {}, chunkid: {}".format(self, chunkid_to_hex(int(chunkid))))

        # chunkid is bignum so we need to serialize it
        chunkid_str = chunkid_to_hex(int(chunkid))
        request_packet = self.generate_packet(["FETCHCHUNK_REQ", {"chunkid": chunkid_str}])

        response_data = await self.__send_rpc_to_mn("FETCHCHUNK_RESP", request_packet)

        if set(response_data.keys()) != {"chunk"}:
            raise ValueError("RPC parameters are wrong for FETCHCHUNK_RESP: %s" % response_data.keys())

        if type(response_data["chunk"]) not in [bytes, type(None)]:
            raise TypeError("chunk is not bytes or None: %s" % type(response_data["chunk"]))

        chunk_data = response_data["chunk"]

        return chunk_data

    async def rpc_download_image(self, imagehash):

        request_packet = self.generate_packet(["IMAGEDOWNLOAD_REQ", {'image_hash': imagehash}])
        response_data = await self.__send_rpc_to_mn("IMAGEDOWNLOAD_RESP", request_packet)

        if response_data['status'] == 'ERROR':
            raise RPCException('Error on IMAGEDOWNLOAD_REQ: {}'.format(response_data['msg']))

        return response_data['image_data']  # bytes. image which is ready to write to the file.

    async def rpc_download_thumbnail(self, thumbnail_hash):

        request_packet = self.generate_packet(["THUMBNAIL_DOWNLOAD_REQ", {'image_hash': thumbnail_hash}])
        response_data = await self.__send_rpc_to_mn("THUMBNAIL_DOWNLOAD_RESP", request_packet)

        return response_data

    async def __send_mn_ticket_rpc(self, rpcreq, rpcresp, data):
        await asyncio.sleep(0)
        request_packet = self.generate_packet([rpcreq, data])
        returned_data = await self.__send_rpc_to_mn(rpcresp, request_packet)
        return returned_data

    async def call_masternode(self, req, resp, data):
        return await self.__send_mn_ticket_rpc(req, resp, data)
