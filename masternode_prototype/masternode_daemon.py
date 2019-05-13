import base64
import asyncio
import signal
import time
import os
import subprocess

import bitcoinrpc

from core_modules.logger import initlogging
from PastelCommon.keys import id_keypair_generation_func
from core_modules.blockchain import BlockChain

from masternode_prototype.masternode_logic import MasterNodeLogic


class MasterNodeDaemon:
    def __init__(self):
        # initialize logging
        self.__logger = initlogging(int(0), __name__)
        self.__logger.debug("Started logger")
        self.basedir = os.getcwd()
        # load or generate keys
        daemon_keys = self.__load_or_create_keys(basedir=os.path.join(os.getcwd(), "keys"),
                                                 privname="private.key", pubname="public.key")
        self.__privkey, self.__pubkey = daemon_keys

        # set up BlockChain object
        self.blockchain = self.__connect_to_daemon()

        # spawn logic
        self.logic = MasterNodeLogic(nodenum=0,
                                     blockchain=self.blockchain,
                                     basedir=self.basedir,
                                     privkey=self.__privkey,
                                     pubkey=self.__pubkey)

    def __load_or_create_keys(self, basedir, privname, pubname):
        # TODO: rethink key generation and audit storage process
        privkeypath = os.path.join(basedir, privname)
        pubkeypath = os.path.join(basedir, pubname)

        # if we need to generate keys, do this now
        if not os.path.isfile(privkeypath) or not os.path.isfile(pubkeypath):
            self.__logger.debug("Key pair for %s and %s does not exist, creating..." % (privname, pubname))
            self.__gen_keys(privkeypath, pubkeypath)

        # open keys
        with open(privkeypath, "rb") as f:
            priv = f.read()
        with open(pubkeypath, "rb") as f:
            pub = f.read()
        return priv, pub

    def __gen_keys(self, privpath, pubpath):
        self.__logger.debug("Generated keys -> private: %s, public: %s" % (privpath, pubpath))

        self.__privkey, self.__pubkey = id_keypair_generation_func()
        with open(privpath, "wb") as f:
            f.write(self.__privkey)
        os.chmod(privpath, 0o0700)
        with open(pubpath, "wb") as f:
            f.write(self.__pubkey)
        os.chmod(pubpath, 0o0700)

    def __connect_to_daemon(self):
        while True:
            blockchain = BlockChain(user='rt',
                                    password='rt',
                                    ip='127.0.0.1',
                                    rpcport=19932)
            try:
                blockchain.getwalletinfo()
            except (ConnectionRefusedError, bitcoinrpc.authproxy.JSONRPCException) as exc:
                self.__logger.debug("Exception %s while getting wallet info, retrying..." % exc)
                time.sleep(0.5)
            else:
                self.__logger.debug("Successfully connected to daemon!")
                break
        return blockchain

    def run_event_loop(self):
        # start async loops
        loop = asyncio.get_event_loop()

        # set signal handlers
        loop.add_signal_handler(signal.SIGTERM, loop.stop)

        loop.create_task(self.logic.zmq_run_forever())
        loop.create_task(self.logic.run_masternode_parser())
        loop.create_task(self.logic.run_ticket_parser())
        loop.create_task(self.logic.run_chunk_fetcher_forever())

        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.stop()
