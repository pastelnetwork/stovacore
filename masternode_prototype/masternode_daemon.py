import asyncio
import signal

from core_modules.logger import initlogging

from masternode_prototype.masternode_logic import MasterNodeLogic, masternodes_refresh_task


class MasterNodeDaemon:
    def __init__(self):
        # initialize logging
        self.__logger = initlogging(int(0), __name__)
        self.__logger.debug("Started logger")

        self.logic = MasterNodeLogic()

    def run_event_loop(self):
        # start async loops
        loop = asyncio.get_event_loop()

        # set signal handlers
        loop.add_signal_handler(signal.SIGTERM, loop.stop)

        loop.create_task(self.logic.run_rpc_server())
        loop.create_task(masternodes_refresh_task())
        # FIXME: ticket parser should rely on cNode ticket API instead of parsing blocks by ourselves.
        # FIXME: we should keep track of known ticket in local database instead of memory.
        # loop.create_task(self.logic.run_ticket_parser())
        loop.create_task(self.logic.run_chunk_fetcher_forever())

        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            # FIXME: such stopping create infinite recursion. Need to close port when stopping.
            # loop.run_until_complete(self.logic.stop_rpc_server())
            loop.stop()
