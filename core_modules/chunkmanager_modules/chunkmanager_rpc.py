import random
import asyncio

from core_modules.http_rpc import RPCException
from core_modules.helpers import hex_to_chunkid, chunkid_to_hex, require_true, get_pynode_digest_hex
from core_modules.logger import initlogging
from core_modules.settings import NetWorkSettings


class ChunkManagerRPC:
    def __init__(self, chunkmanager, mn_manager, aliasmanager):
        self.__logger = initlogging('', __name__)
        self.__chunkmanager = chunkmanager
        self.__aliasmanager = aliasmanager
        self.__mn_manager = mn_manager

    async def issue_random_tests_forever(self, waittime, number_of_chunks=1):
        while True:
            await asyncio.sleep(waittime)

            chunks = self.__chunkmanager.select_random_chunks_we_have(number_of_chunks)
            for chunk in chunks:
                self.__logger.debug("Selected chunk %s for random check" % chunkid_to_hex(chunk.chunkid))

                # get chunk
                data = self.__chunkmanager.get_chunk(chunk)

                # pick a random range
                require_true(len(data) > 1024)
                start = random.randint(0, len(data)-1024)
                end = start + 1024

                # calculate digest
                digest = get_pynode_digest_hex(data[start:end])
                self.__logger.debug("Digest for range %s - %s is: %s" % (start, end, digest))

                # find owners for all the alt keys who are not us
                owners = self.__aliasmanager.find_other_owners_for_chunk(chunk.chunkid)

                # call RPC on all other MNs
                for owner in owners:
                    mn = self.__mn_manager.get(owner)

                    try:
                        response_digest = await mn.send_rpc_spotcheck(chunk.chunkid, start, end)
                    except RPCException as exc:
                        self.__logger.info("SPOTCHECK RPC FAILED for node %s with exception %s" % (owner, exc))
                    else:
                        if response_digest != digest:
                            self.__logger.warning("SPOTCHECK FAILED for node %s (%s != %s)" % (owner, digest,
                                                                                               response_digest))
                        else:
                            self.__logger.debug("SPOTCHECK SUCCESS for node %s for chunk: %s" % (owner, digest))

                    # TODO: track successes/errors

    def receive_rpc_spotcheck(self, data):
        # NOTE: data is untrusted!
        if not isinstance(data, dict):
            raise TypeError("Data must be a dict!")

        if set(data.keys()) != {"chunkid", "start", "end"}:
            raise ValueError("Invalid arguments for spotcheck: %s" % (data.keys()))

        for k, v in data.items():
            if k in ["start", "end"]:
                if not isinstance(v, int):
                    raise TypeError("Invalid type for key %s in spotcheck" % k)
            else:
                if not isinstance(v, str):
                    raise TypeError("Invalid type for key %s in spotcheck" % k)

        chunkid = hex_to_chunkid(data["chunkid"])
        start = data["start"]
        end = data["end"]

        # check if start and end are within parameters
        if start < 0:
            raise ValueError("start is < 0")
        if start >= end:
            raise ValueError("start >= end")
        if start > NetWorkSettings.CHUNKSIZE or end > NetWorkSettings.CHUNKSIZE:
            raise ValueError("start > CHUNKSIZE or end > CHUNKSIZE")

        # we don't actually need the full chunk here, but we get it anyway as we are running verify() on it
        chunk = self.__chunkmanager.get_chunk_if_we_have_it(chunkid)
        if chunk is not None:
            # generate digest
            data = chunk[start:end]
            digest = get_pynode_digest_hex(data)
        else:
            self.__logger.info("We failed spotcheck for chunk %s" % chunkid_to_hex(chunkid))
            # return a bogus hash
            digest = get_pynode_digest_hex(b'DATA WAS NOT FOUND')

        return {"digest": digest}

    def receive_rpc_fetchchunk(self, data, **kwargs):
        # NOTE: data is untrusted!
        if not isinstance(data, dict):
            raise TypeError("Data must be a dict!")

        if set(data.keys()) != {"chunkid"}:
            raise ValueError("Invalid arguments for spotcheck: %s" % (data.keys()))

        if not isinstance(data["chunkid"], str):
            raise TypeError("Invalid type for key chunkid in spotcheck")

        chunkid = hex_to_chunkid(data["chunkid"])

        chunk = self.__chunkmanager.get_chunk_if_we_have_it(chunkid)

        return {"chunk": chunk}
