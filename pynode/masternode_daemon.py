import asyncio
import signal

from core_modules.artregistry import ArtRegistry
from core_modules.autotrader import AutoTrader
from core_modules.masternode_ticketing import ArtRegistrationServer
from core_modules.settings import Settings
from pynode.rpc_server import RPCServer
from core_modules.logger import initlogging

from pynode.tasks import masternodes_refresh_task, index_new_chunks_task, \
    process_new_tickets_task, proccess_tmp_storage, chunk_fetcher_task


class MasterNodeDaemon:
    """
    In `run_event_loop` here are everything Masternode does:
     - RPC server (listening for incoming connections). Under the hood - it's aiohttp server.
     - `chunk_fetcher_task` - high-level logic for the chunk storage (find out which chunks we miss and download them)
     - `masternodes_refresh_task` - maintain masternode list in actual state (updates DB).
     - `index_new_chunks_task` - calculates XOR distances for MNs and new chunks
     - `process_new_tickets_task` - adds new chunks to the database (from Activation tickets)
     - `proccess_tmp_storage` - Auxilary task for the chunkstorage. Moves confirmed chunks from tmp storage to
     persistant one.
    """
    def __init__(self):
        # initialize logging
        self.__logger = initlogging(int(0), __name__, Settings.LOG_LEVEL)
        self.__logger.debug("Started logger")
        self.rpcserver = RPCServer()

        # legacy entities. Review and delete if not required
        self.__artregistry = ArtRegistry()
        self.__autotrader = AutoTrader(self.__artregistry)
        self.__artregistrationserver = ArtRegistrationServer()
        # end of legacy entities

        for rpc_handler in self.__artregistrationserver.rpc_handler_list:
            self.rpcserver.add_callback(*rpc_handler)

    def run_event_loop(self):
        # start async loops
        loop = asyncio.get_event_loop()

        # set signal handlers
        loop.add_signal_handler(signal.SIGTERM, loop.stop)

        loop.create_task(self.rpcserver.run_server())
        loop.create_task(chunk_fetcher_task())

        # refresh masternode list, calculate XOR distances for added masternode
        loop.create_task(masternodes_refresh_task())

        # calculate XOR distances for new chunks
        loop.create_task(index_new_chunks_task())

        # fetch new activation tickets, process chunks from there
        loop.create_task(process_new_tickets_task())

        # go through temp storage, move confirmed chunks to persistent one
        loop.create_task(proccess_tmp_storage())

        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.stop()
