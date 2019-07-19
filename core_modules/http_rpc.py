import asyncio
import ssl
from aiohttp import web, ClientSession

from core_modules.logger import initlogging
from core_modules.rpc_serialization import pack_and_sign, verify_and_unpack
from core_modules.helpers import chunkid_to_hex
from core_modules.settings import NetWorkSettings


class RPCException(Exception):
    pass


class RPCClient:
    def __init__(self, privkey, pubkey, nodeid, server_ip, server_port, mnpubkey):
        if type(nodeid) is not int:
            raise TypeError("nodeid must be int!")

        self.__logger = initlogging('', __name__, level="debug")

        # variables of the client
        self.__privkey = privkey
        self.__pubkey = pubkey

        # variables of the server (the MN)
        self.__server_nodeid = nodeid
        self.__server_ip = server_ip
        self.__server_port = server_port
        self.__server_pubkey = mnpubkey

        # pubkey and nodeid should be public for convenience, so that we can identify which server this is
        self.pubkey = self.__server_pubkey
        self.nodeid = nodeid

        # TODO
        self.__reputation = None

    def __str__(self):
        return str(self.__server_nodeid)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    # TODO: unify this with the other one in MasterNodeLogic
    def __return_rpc_packet(self, sender_id, msg):
        response_packet = pack_and_sign(self.__privkey,
                                        self.__pubkey,
                                        sender_id, msg)
        return response_packet

    async def __send_rpc_and_wait_for_response(self, msg):
        url = 'https://{}:{}/'.format(self.__server_ip, self.__server_port)
        self.__logger.info('Sending RPC message to {}'.format(url))
        async with ClientSession() as session:
            async with session.post(url, data=msg, ssl=False) as resp:
                self.__logger.info('RPC request sent, waiting for response')
                msg = await resp.read()
                self.__logger.info('RPC response received')
                return msg

    async def __send_rpc_to_mn(self, response_name, request_packet):
        await asyncio.sleep(0)

        response_packet = await self.__send_rpc_and_wait_for_response(request_packet)

        sender_id, response_msg = verify_and_unpack(response_packet, self.__pubkey)

        rpcname, success, response_data = response_msg

        if rpcname != response_name:
            raise ValueError("Spotcheck response has rpc name: %s" % rpcname)

        if success != "SUCCESS":
            self.__logger.warn('Error from masternode {}'.format(self.__server_ip))
            raise RPCException(response_msg)

        return response_data

    async def send_rpc_ping(self, data):
        await asyncio.sleep(0)

        request_packet = self.__return_rpc_packet(self.__server_pubkey, ["PING_REQ", data])

        try:
            returned_data = await self.__send_rpc_to_mn("PING_RESP", request_packet)
        except:
            self.__logger.warn('Skipping by timout')
            return None

        if set(returned_data.keys()) != {"data"}:
            raise ValueError("RPC parameters are wrong for PING RESP: %s" % returned_data.keys())

        if type(returned_data["data"]) != bytes:
            raise TypeError("data is not bytes: %s" % type(returned_data["data"]))

        response_data = returned_data["data"]

        return response_data

    async def send_rpc_spotcheck(self, chunkid, start, end):
        await asyncio.sleep(0)

        self.__logger.debug("SPOTCHECK REQUEST to %s, chunkid: %s" % (self, chunkid_to_hex(chunkid)))

        # chunkid is bignum so we need to serialize it
        chunkid_str = chunkid_to_hex(chunkid)
        request_packet = self.__return_rpc_packet(self.__server_pubkey, ["SPOTCHECK_REQ", {"chunkid": chunkid_str,
                                                                                           "start": start,
                                                                                           "end": end}])

        response_data = await self.__send_rpc_to_mn("SPOTCHECK_RESP", request_packet)

        if set(response_data.keys()) != {"digest"}:
            raise ValueError("RPC parameters are wrong for SPOTCHECK_RESP: %s" % response_data.keys())

        if type(response_data["digest"]) != str:
            raise TypeError("digest is not str: %s" % type(response_data["digest"]))

        response_digest = response_data["digest"]

        self.__logger.debug("SPOTCHECK RESPONSE from %s, msg: %s" % (self, response_digest))

        return response_digest

    async def send_rpc_fetchchunk(self, chunkid):
        await asyncio.sleep(0)

        self.__logger.debug("FETCHCHUNK REQUEST to %s, chunkid: %s" % (self, chunkid_to_hex(chunkid)))

        # chunkid is bignum so we need to serialize it
        chunkid_str = chunkid_to_hex(chunkid)
        request_packet = self.__return_rpc_packet(self.__server_pubkey, ["FETCHCHUNK_REQ", {"chunkid": chunkid_str}])

        response_data = await self.__send_rpc_to_mn("FETCHCHUNK_RESP", request_packet)

        if set(response_data.keys()) != {"chunk"}:
            raise ValueError("RPC parameters are wrong for FETCHCHUNK_RESP: %s" % response_data.keys())

        if type(response_data["chunk"]) not in [bytes, type(None)]:
            raise TypeError("chunk is not bytes or None: %s" % type(response_data["chunk"]))

        chunk = response_data["chunk"]

        return chunk

    async def __send_mn_ticket_rpc(self, rpcreq, rpcresp, data):
        await asyncio.sleep(0)
        request_packet = self.__return_rpc_packet(self.__server_pubkey, [rpcreq, data])
        self.__logger.info('Sending mn ticket to RPC')
        returned_data = await self.__send_rpc_to_mn(rpcresp, request_packet)
        return returned_data

    async def call_masternode(self, req, resp, data):
        return await self.__send_mn_ticket_rpc(req, resp, data)


class RPCServer:
    def __init__(self, nodenum, ip, port, privkey, pubkey):
        self.__logger = initlogging('', __name__)

        self.__nodenum = nodenum
        self.__ip = ip
        self.__port = port
        self.__privkey = privkey
        self.__pubkey = pubkey
        self.runner = None
        self.site = None

        # define our RPCs
        self.__RPCs = {}
        self.app = web.Application()
        self.app.add_routes([web.post('/', self.__http_proccess)])
        # self.app.on_shutdown.append(self.stop_server)

        self.__logger.debug("RPC listening on {}".format(self.__port))

        # add our only call
        self.add_callback("PING_REQ", "PING_RESP", self.__receive_rpc_ping)

    def add_callback(self, callback_req, callback_resp, callback_function, coroutine=False, allowed_pubkey=None):
        self.__RPCs[callback_req] = [callback_resp, callback_function, coroutine, allowed_pubkey]

    def __receive_rpc_ping(self, data):
        self.__logger.info('Ping request received')
        if not isinstance(data, bytes):
            raise TypeError("Data must be a bytes!")

        return {"data": data}

    def __return_rpc_packet(self, sender_id, msg):
        response_packet = pack_and_sign(self.__privkey,
                                        self.__pubkey,
                                        sender_id, msg)
        return response_packet

    async def __process_local_rpc(self, sender_id, rpcname, data):
        self.__logger.debug("Received RPC %s" % rpcname)
        # get the appropriate rpc function or send back an error
        rpc = self.__RPCs.get(rpcname)
        if rpc is None:
            self.__logger.info("RPC %s is not implemented, ignoring packet!" % rpcname)

        # figure out which RPC this is
        response_name, fn, coroutine, allowed_pubkey = self.__RPCs.get(rpcname)

        # check ACLs
        if allowed_pubkey is not None and allowed_pubkey != sender_id:
            self.__logger.warning("RPC ACL failed: %s does not match %s for RPC %s" % (
                allowed_pubkey, sender_id, rpcname))
            msg = [response_name, "ERROR", "ACL ERROR"]
        else:
            # call the RPC function, catch all exceptions
            try:
                # handle callback depending on whether or not it's old-style blocking or new-style coroutine
                if not coroutine:
                    ret = fn(data, sender_id=sender_id)
                else:
                    ret = await fn(data, sender_id=sender_id)
            except Exception as exc:
                self.__logger.exception("Exception received while doing RPC: %s" % exc)
                msg = [response_name, "ERROR", "RPC ERROR happened: %s" % exc]
            else:
                # generate response if everything went well
                msg = [response_name, "SUCCESS", ret]

        ret = self.__return_rpc_packet(sender_id, msg)
        self.__logger.debug("Done with RPC RPC %s" % rpcname)
        return ret

    async def __http_proccess(self, request):
        msg = await request.content.read()
        sender_id, received_msg = verify_and_unpack(msg, self.__pubkey)
        rpcname, data = received_msg
        reply_packet = await self.__process_local_rpc(sender_id, rpcname, data)

        return web.Response(body=reply_packet)

    async def run_server(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(NetWorkSettings.HTTPS_CERTIFICATE_FILE,
                                    NetWorkSettings.HTTPS_KEY_FILE)
        self.site = web.TCPSite(self.runner, port=self.__port, ssl_context=ssl_context)
        await self.site.start()

    async def stop_server(self, *args, **kwargs):
        print('Stopping server')
        await self.runner.cleanup()
