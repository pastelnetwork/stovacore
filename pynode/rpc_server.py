import ssl
from os import path

from aiohttp import web

from core_modules.database import Masternode
from core_modules.logger import initlogging
from core_modules.rpc_serialization import RPCMessage
from core_modules.settings import Settings
from pynode.rpc_handlers import receive_rpc_fetchchunk, receive_rpc_download_image, receive_rpc_download_thumbnail


class RPCServer:
    def __init__(self):
        self.__logger = initlogging('RPC Server', __name__)

        self.runner = None
        self.site = None

        # define our RPCs
        self.__RPCs = {}
        self.app = web.Application()
        self.app.add_routes([web.post('/', self.__http_proccess), web.get('/status', self.get_status)])
        # self.app.on_shutdown.append(self.stop_server)

        self.__logger.debug("Starting RPC to listen on {}".format(Settings.RPC_PORT))

        # MUST be removed before release -->
        self.add_callback("PING_REQ", "PING_RESP", self.__receive_rpc_ping)
        self.add_callback("SQL_REQ", "SQL_RESP", self.__receive_rpc_sql)
        # <--

        self.add_callback("FETCHCHUNK_REQ", "FETCHCHUNK_RESP",
                          receive_rpc_fetchchunk)
        self.add_callback("IMAGEDOWNLOAD_REQ", "IMAGEDOWNLOAD_RESP",
                          receive_rpc_download_image)

        self.add_callback("THUMBNAIL_DOWNLOAD_REQ", "THUMBNAIL_DOWNLOAD_RESP",
                          receive_rpc_download_thumbnail)

        self.__logger.debug("RPC Server initialized")

    def add_callback(self, callback_req, callback_resp, callback_function, coroutine=False, allowed_pubkey=None):
        self.__RPCs[callback_req] = [callback_resp, callback_function, coroutine, allowed_pubkey]

    async def get_status(self, request):
        self.__logger.info('Status request received')
        masternodes = list(Masternode.get_active_nodes())
        result = { "status": "alive", "details": {"masternode_count": len(masternodes)}}
        return web.json_response(result)

    def __receive_rpc_ping(self, data, *args, **kwargs):
        self.__logger.info('Ping request received')
        if not isinstance(data, bytes):
            raise TypeError("Data must be a bytes!")
        return {"data": data}

    def __receive_rpc_sql(self, sql, *args, **kwargs):
        self.__logger.info('SQL request received')
        if not isinstance(sql, str):
            raise TypeError("SQL must be a string!")
        from core_modules.database import MASTERNODE_DB
        c = MASTERNODE_DB.execute_sql(sql)
        r = c.fetchall()
        result = []
        fields = [x[0] for x in c.description]
        for record in r:
            dict_record = dict()
            for i in range(len(record)):
                dict_record[fields[i]] = record[i]
            result.append(dict_record)
        return {"result": result}

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
        rpc_message = RPCMessage(msg, sender_id)
        ret = rpc_message.pack()
        self.__logger.debug("Done with RPC RPC %s" % rpcname)
        return ret

    async def __http_proccess(self, request):
        msg = await request.content.read()
        rpc_message = RPCMessage.reconstruct(msg)
        sender_id, received_msg = rpc_message.sender_id, rpc_message.data

        rpcname, data = received_msg
        reply_packet = await self.__process_local_rpc(sender_id, rpcname, data)

        return web.Response(body=reply_packet)

    async def run_server(self):
        if not path.exists(Settings.HTTPS_CERTIFICATE_FILE):
            print("ERROR! HTTPS Certificate file doesn't exist - {0}", Settings.HTTPS_CERTIFICATE_FILE)
            raise SystemExit('Exiting')
        if not path.exists(Settings.HTTPS_KEY_FILE):
            print("ERROR! HTTPS Certificate Key file doesn't exist - {0}", Settings.HTTPS_KEY_FILE)
            raise SystemExit('Exiting')

        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(Settings.HTTPS_CERTIFICATE_FILE,
                                    Settings.HTTPS_KEY_FILE)
        self.site = web.TCPSite(self.runner, port=Settings.RPC_PORT, ssl_context=ssl_context)
        await self.site.start()

    async def stop_server(self, *args, **kwargs):
        print('Stopping server')
        await self.runner.cleanup()
