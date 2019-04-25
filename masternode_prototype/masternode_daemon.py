import base64
import asyncio
import signal
import time
import os
import subprocess

import bitcoinrpc

from core_modules.logger import initlogging
from core_modules.settings import MNDeamonSettings, NetWorkSettings
from PastelCommon.keys import id_keypair_generation_func
from core_modules.blockchain import BlockChain

from masternode_prototype.masternode_logic import MasterNodeLogic


class MasterNodeDaemon:
    def __init__(self, settings, addnodes=None):
        # initialize logging
        self.__logger = initlogging(int(settings["nodename"]), __name__)
        self.__logger.debug("Started logger")

        self.__settings = MNDeamonSettings(settings)
        self.__addnodes = addnodes
        self.__nodenum = settings["nodename"]

        # processes
        self.__cmnprocess = None
        self.__djangoprocess = None

        # load or generate keys
        daemon_keys = self.__load_or_create_keys(basedir=os.path.join(self.__settings.basedir, "config"),
                                                 privname="private.key", pubname="public.key")
        self.__privkey, self.__pubkey = daemon_keys

        django_keys = self.__load_or_create_keys(basedir=os.path.join(self.__settings.basedir, "config"),
                                                 privname="django_private.key", pubname="django_public.key")
        self.__django_privkey, self.__django_pubkey = django_keys

        # start actual blockchain daemon process
        self.__start_cmn()

        # start the django process
        self.__start_django()

        # set up BlockChain object
        self.blockchain = self.__connect_to_daemon()

        # spawn logic
        self.logic = MasterNodeLogic(nodenum=self.__nodenum,
                                     blockchain=self.blockchain,
                                     basedir=self.__settings.basedir,
                                     privkey=self.__privkey,
                                     pubkey=self.__pubkey,
                                     ip=self.__settings.ip,
                                     port=self.__settings.pyrpcport,
                                     django_pubkey=self.__django_pubkey)

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

    def __start_django(self):
        http_port = str(self.__settings.pyhttpadmin)
        pastel_basedir = self.__settings.datadir
        patel_rpc_ip = self.__settings.ip
        pastel_rpc_port = str(self.__settings.pyrpcport)
        pastel_rpc_pubkey = base64.b64encode(self.__pubkey)

        cmdline = NetWorkSettings.DJANGOCMDLINE + [http_port, pastel_basedir, patel_rpc_ip, pastel_rpc_port, pastel_rpc_pubkey]

        self.__djangoprocess = subprocess.Popen(cmdline, cwd=NetWorkSettings.BASEDIR)

    def __stop_django(self):
        self.__djangoprocess.terminate()
        self.__djangoprocess.wait()

    def __start_cmn(self):
        self.__logger.debug("Starting bitcoing daemon on rpcport %s" % self.__settings.rpcport)
        cmdline = [
            NetWorkSettings.BLOCKCHAIN_BINARY,
            "-rpcuser=%s" % self.__settings.rpcuser,
            "-rpcpassword=%s" % self.__settings.rpcpassword,
            "-testnet=1",
            # "-regtest=1",
            "-dnsseed=0",
            # "-gen=1",
            "-debug=1",
            "-genproclimit=1",
            "-equihashsolver=tromp",
            "-showmetrics=0",
            "-listenonion=0",
            "-onlynet=ipv4",
            "-txindex",
            "-rpcport=%s" % self.__settings.rpcport,
            "-port=%s" % self.__settings.port,
            "-server",
            "-addresstype=legacy",
            "-discover=0",
            "-datadir=%s" % self.__settings.datadir
        ]

        if self.__addnodes is not None:
            for nodeaddress in self.__addnodes:
                self.__logger.debug("Adding extra node %s to cmdline with -addnode" % nodeaddress)
                cmdline.append("-addnode=%s" % nodeaddress)

        self.__cmnprocess = subprocess.Popen(cmdline, cwd=NetWorkSettings.BASEDIR)

    def __stop_cmn(self):
        self.__cmnprocess.terminate()
        self.__cmnprocess.wait()

    def __connect_to_daemon(self):
        while True:
            blockchain = BlockChain(user=self.__settings.rpcuser,
                                    password=self.__settings.rpcpassword,
                                    ip=self.__settings.ip,
                                    rpcport=self.__settings.rpcport)
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
        loop.create_task(self.logic.run_django_tasks_forever())
        # loop.create_task(self.logic.run_heartbeat_forever())
        # loop.create_task(self.logic.run_ping_test_forever())
        # loop.create_task(self.logic.issue_random_tests_forever(1))
        loop.create_task(self.logic.run_chunk_fetcher_forever())

        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.stop()
        self.__stop_cmn()
        self.__stop_django()
