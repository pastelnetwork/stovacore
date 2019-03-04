import os
import asyncio
import logging

from django.conf import settings
from core_modules.zmq_rpc import RPCClient
from core_modules.helpers import get_nodeid_from_pubkey


def initlogging():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(' %(asctime)s - ' + "%s - %s" % (__name__, os.getpid()) + ' - %(levelname)s - %(message)s')
    consolehandler = logging.StreamHandler()
    consolehandler.setFormatter(formatter)
    logger.addHandler(consolehandler)
    return logger


logger = initlogging()


class ClientConnection:
    def __init__(self):
        self.__privkey = None
        self.__pubkey = None
        self.pubkey = None
        self.__rpcclient = None

    def __initialize(self):
        # internal keys used for RPC between Django and the backend
        self.__privkey = open(settings.PASTEL_DJANGO_PRIVKEY, "rb").read()
        self.__pubkey = open(settings.PASTEL_DJANGO_PUBKEY, "rb").read()

        # trade_pubkey - this is the key the backend uses for trading
        self.pubkey = open(settings.PASTEL_TRADE_PUBKEY, "rb").read()
        self.privkey = open(settings.PASTEL_TRADE_PRIVKEY, "rb").read()

        # we need the server's nodeid, ip, port, pubkey
        self.__rpcclient = RPCClient(settings.PASTEL_NODENUM, self.__privkey, self.__pubkey,
                                     get_nodeid_from_pubkey(self.pubkey), settings.PASTEL_RPC_IP,
                                     settings.PASTEL_RPC_PORT, settings.PASTEL_RPC_PUBKEY)

    def __call_rpc(self, task):
        # get event loop, or start a new one
        need_new_loop = False
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            need_new_loop = True
        else:
            if loop.is_closed():
                need_new_loop = True

        if need_new_loop:
            asyncio.set_event_loop(asyncio.new_event_loop())
            loop = asyncio.get_event_loop()

        future = asyncio.ensure_future(task, loop=loop)

        result = loop.run_until_complete(future)

        loop.stop()
        loop.close()
        return result

    def call(self, *args):
        if self.__privkey is None:
            self.__initialize()
        return self.__call_rpc(self.__rpcclient.call_masternode("DJANGO_REQ", "DJANGO_RESP", args))

    def get_pubkey(self):
        if not self.pubkey:
            self.__initialize()
        return self.pubkey

    def get_privkey(self):
        if not self.privkey:
            self.__initialize()
        return self.privkey

client = ClientConnection()
