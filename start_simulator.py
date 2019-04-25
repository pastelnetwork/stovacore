import time
import logging
import signal
import asyncio
import sys
import os
import multiprocessing

from masternode_prototype.masternode_daemon import MasterNodeDaemon
from core_modules.masternode_discovery import discover_nodes
from PastelCommon.keys import id_keypair_generation_func


class Simulator:
    def __init__(self, configdir):
        self.__name = "spawner"
        self.__logger = self.__initlogging()
        self.__configdir = configdir

        # generate our keys for RPC
        self.__privkey, self.__pubkey = id_keypair_generation_func()

    def __initlogging(self):
        logger = logging.getLogger(self.__name)
        logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(' %(asctime)s - ' + self.__name + ' - %(levelname)s - %(message)s')
        consolehandler = logging.StreamHandler()
        consolehandler.setFormatter(formatter)
        logger.addHandler(consolehandler)
        return logger

    def spawn_masternode(self, settings, addnodes):
        self.__logger.debug("Starting masternode: %s" % settings["nodename"])
        mn = MasterNodeDaemon(settings=settings, addnodes=addnodes)
        mn.run_event_loop()
        self.__logger.debug("Stopped spawned masternode: %s" % settings["nodename"])

    def start_masternode_in_new_process(self, settings_list, addnodes):
        masternodes = {}
        for settings in settings_list:
            os.makedirs(settings["basedir"], exist_ok=True)
            os.makedirs(os.path.join(settings["basedir"], "config"), exist_ok=True)

            p = multiprocessing.Process(target=self.spawn_masternode, args=(settings, addnodes))
            p.start()

            nodename = settings["nodename"]
            masternodes[nodename] = p
            self.__logger.debug("Found masternode %s!" % nodename)

            # if len(masternodes) > 1:
            #     self.__logger.debug("ABORTING EARLY")
            #     break

        return masternodes

    def main(self):
        # spawn MasterNode Daemons
        settings_list = discover_nodes(self.__configdir)
        addnodes = ["%s:%s" % (x["ip"], x["port"]) for x in settings_list]
        masternodes = self.start_masternode_in_new_process(settings_list, addnodes)

        # start our event loop
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGTERM, loop.stop)
        loop.add_signal_handler(signal.SIGINT, loop.stop)

        # run loop until Ctrl-C
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.stop()

        # clean up
        for nodeid, mn in masternodes.items():
            self.__logger.debug("Stopping MN %s" % nodeid)
            if mn.is_alive():
                os.kill(mn.pid, signal.SIGTERM)

        while any([mn.is_alive() for mn in masternodes.values()]):
            self.__logger.debug("Waiting for MNs to stop")
            time.sleep(0.5)

        self.__logger.debug("Stopped, you may press Ctrl-C again")


if __name__ == "__main__":
    regtestdir = sys.argv[1]

    simulator = Simulator(configdir=regtestdir)
    simulator.main()
