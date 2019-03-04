import subprocess
import os
import tempfile
import shutil
import time

import bitcoinrpc

from core_modules.settings import NetWorkSettings

from core_modules.blockchain import BlockChain


class Daemon:
    def __init__(self, rpcuser, rpcpassword, rpcport, ip, port):
        self.rpcuser = rpcuser
        self.rpcpassword = rpcpassword
        self.rpcport = rpcport
        self.ip = ip
        self.port = port

        self.__process = None
        self.__test_dir = None

    def start(self):
        self.__test_dir = tempfile.mkdtemp()

        animecoin_conf = os.path.join(self.__test_dir, "animecoin.conf")

        # create empty animecoin.conf
        with open(animecoin_conf, "w") as f:
            pass

        cmdline = [
            NetWorkSettings.BLOCKCHAIN_BINARY,
            "-rpcuser=%s" % self.rpcuser,
            "-rpcpassword=%s" % self.rpcpassword,
            "-regtest=1",
            "-dnsseed=0",
            # "-gen=1",
            "-debug=1",
            "-genproclimit=1",
            "-equihashsolver=tromp",
            "-showmetrics=0",
            "-listenonion=0",
            "-onlynet=ipv4",
            "-txindex",
            "-rpcport=%s" % self.rpcport,
            "-port=%s" % self.port,
            "-server",
            "-addresstype=legacy",
            "-discover=0",
            "-datadir=%s" % self.__test_dir,
        ]

        self.__process = subprocess.Popen(cmdline, cwd=NetWorkSettings.BASEDIR)

    def stop(self):
        if self.__process is not None:
            self.__process.terminate()
            self.__process.wait()

        shutil.rmtree(self.__test_dir)

    def connect(self):
        # connect to daemon
        while True:
            blockchain = BlockChain(user=self.rpcuser,
                                    password=self.rpcpassword,
                                    ip=self.ip,
                                    rpcport=self.rpcport)
            try:
                blockchain.getwalletinfo()
            except (ConnectionRefusedError, bitcoinrpc.authproxy.JSONRPCException) as exc:
                time.sleep(0.5)
            else:
                return blockchain
