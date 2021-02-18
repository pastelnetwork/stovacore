"""
This file contains MasterNodeDaemon class which `run_event_loop` is basically pynode entry point.
"""
import asyncio
import signal

from core_modules.masternode_ticketing import RPC_HANDLER_LIST
from pynode.rpc_server import RPCServer
from core_modules.logger import get_logger

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
        self.__logger = get_logger('Masternode Daemon')

        self.rpcserver = RPCServer()

        for rpc_handler in RPC_HANDLER_LIST:
            self.rpcserver.add_callback(*rpc_handler)
        self.__logger.debug("Art Registration callback handlers set")

        self.__logger.debug("Masternode Daemon initialized")

    def run_event_loop(self):
        self.__logger.debug("Starting event loop...")

        # start async loops
        loop = asyncio.get_event_loop()

        # set signal handlers
        loop.add_signal_handler(signal.SIGTERM, loop.stop)

        loop.create_task(self.rpcserver.run_server())

        loop.create_task(chunk_fetcher_task())

        # refresh masternode list, calculate XOR distances for added masternode
        loop.create_task(masternodes_refresh_task())
        self.__logger.debug("Masternode refresh task started")

        # calculate XOR distances for new chunks
        loop.create_task(index_new_chunks_task())

        # fetch new activation tickets, process chunks from there
        loop.create_task(process_new_tickets_task())
        self.__logger.debug("Ticket processor started")

        # go through temp storage, move confirmed chunks to persistent one
        loop.create_task(proccess_tmp_storage())
        self.__logger.debug("Storage processor started")

        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.stop()
