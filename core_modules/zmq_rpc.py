import asyncio

import zmq
import zmq.asyncio
import uuid

from core_modules.logger import initlogging
from core_modules.rpc_serialization import pack_and_sign, verify_and_unpack
from core_modules.helpers import get_cnode_digest_hex, chunkid_to_hex


class RPCException(Exception):
    pass


class RPCClient:
    def __init__(self, nodenum, privkey, pubkey, nodeid, server_ip, server_port, mnpubkey):
        if type(nodeid) is not int:
            raise TypeError("nodeid must be int!")

        self.__logger = initlogging(nodenum, __name__, level="debug")

        # variables of the client
        self.__privkey = privkey
        self.__pubkey = pubkey

        # variables of the server (the MN)
        self.__server_nodeid = nodeid
        self.__server_ip = server_ip
        self.__server_port = server_port
        self.__server_pubkey = mnpubkey

        self.__outstanding_responses = {}

        self.__zmq = None

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
        ctx = zmq.asyncio.Context()
        if self.__zmq is None:
            self.__zmq = ctx.socket(zmq.DEALER)
            # TODO: make sure identity handling is correct and secure
            self.__zmq.setsockopt(zmq.IDENTITY, bytes(str(uuid.uuid4()), "utf-8"))
            self.__zmq.connect("tcp://%s:%s" % (self.__server_ip, self.__server_port))

        # we use the msgid to figure out which coroutine the response belongs to
        send_msgid = uuid.uuid4().bytes

        while True:
            try:
                await self.__zmq.send_multipart([send_msgid, msg], flags=zmq.NOBLOCK)
                self.__logger.info('RPC message is sent, server IP: {}'.format(self.__server_ip))
            except zmq.error.Again:
                await asyncio.sleep(0.01)
            else:
                break
        counter = 0
        # on receive we have to make sure that the message we get back belongs to this particular coroutine
        while True:
            # if counter > 400:
            #     raise Exception('No response for 4 seconds - skipping')
            # has another coroutine received our message?
            if send_msgid in self.__outstanding_responses:
                msg = self.__outstanding_responses[send_msgid]
                del self.__outstanding_responses[send_msgid]
                self.__logger.info('RPC response received')
                return msg

            # try to fetch the next message
            try:
                recv_msgid, msg = await self.__zmq.recv_multipart(flags=zmq.NOBLOCK)  # waits for msg to be ready
            except zmq.error.Again:
                counter += 1
                await asyncio.sleep(0.01)
            else:
                # does this message belong to us?
                if recv_msgid != send_msgid:
                    self.__outstanding_responses[recv_msgid] = msg
                    continue
                else:
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
        self.__logger = initlogging(nodenum, __name__)

        self.__nodenum = nodenum
        self.__ip = ip
        self.__port = port
        self.__privkey = privkey
        self.__pubkey = pubkey

        # our RPC socket
        self.__zmq = zmq.asyncio.Context().socket(zmq.ROUTER)
        self.__zmq.setsockopt(zmq.IDENTITY, bytes(str(self.__nodenum), "utf-8"))
        bindaddr = "tcp://%s:%s" % (self.__ip, self.__port)
        self.__zmq.bind(bindaddr)
        self.__logger.debug("RPC listening on %s" % bindaddr)

        # define our RPCs
        self.__RPCs = {}

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
                    ret = fn(data)
                else:
                    ret = await fn(data)
            except Exception as exc:
                self.__logger.exception("Exception received while doing RPC: %s" % exc)
                msg = [response_name, "ERROR", "RPC ERROR happened: %s" % exc]
            else:
                # generate response if everything went well
                msg = [response_name, "SUCCESS", ret]

        ret = self.__return_rpc_packet(sender_id, msg)
        self.__logger.debug("Done with RPC RPC %s" % rpcname)
        return ret

    async def __zmq_process(self, ident, msgid, msg):
        # TODO: authenticate RPC, only allow from other MNs
        sender_id, received_msg = verify_and_unpack(msg, self.__pubkey)
        rpcname, data = received_msg

        reply_packet = await self.__process_local_rpc(sender_id, rpcname, data)

        while True:
            try:
                await self.__zmq.send_multipart([ident, msgid, reply_packet], flags=zmq.NOBLOCK)
            except zmq.error.Again:
                await asyncio.sleep(0.01)
            else:
                break

    async def zmq_run_once(self):
        while True:
            try:
                ident, msgid, msg = await self.__zmq.recv_multipart(flags=zmq.NOBLOCK)  # waits for msg to be ready
            except zmq.error.Again:
                await asyncio.sleep(0.01)
            else:
                break

        asyncio.ensure_future(self.__zmq_process(ident, msgid, msg))

    async def zmq_run_forever(self):
        while True:
            await self.zmq_run_once()
