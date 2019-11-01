import asyncio
import signal

from core_modules.logger import initlogging

from pynode.masternode_logic import MasterNodeLogic, masternodes_refresh_task, index_new_chunks_task, \
    process_new_tickets_task, proccess_tmp_storage


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
        loop.create_task(self.logic.run_chunk_fetcher_forever())

        # refresh masternode list, calculate XOR distances for added masternode
        loop.create_task(masternodes_refresh_task())

        # calculate XOR distances for new chunks
        loop.create_task(index_new_chunks_task())

        # fetch new activation tickets, process chunks from there
        loop.create_task(process_new_tickets_task())

        # go through temp storage, move confirmed chunks to persistent one
        loop.create_task(proccess_tmp_storage())

        # FIXME: old ticket_parser is replaced with `process_new_tickets_task`, left here for reference.
        # TODO: remove when it'll be clear that nothing from there is needed.
        # loop.create_task(self.logic.run_ticket_parser())

        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.stop()
