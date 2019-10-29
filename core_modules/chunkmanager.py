import os
import random

from datetime import datetime as dt

from core_modules.helpers import get_pynode_digest_int
from core_modules.chunk_storage import ChunkStorage
from core_modules.helpers import chunkid_to_hex
from core_modules.settings import NetWorkSettings
from core_modules.logger import initlogging
from cnode_connection import basedir, get_blockchain_connection


class Chunk:
    def __init__(self, chunkid):
        if type(chunkid) != int:
            raise ValueError("chunkid is not int!")

        self.chunkid = chunkid
        self.verified = False
        self.is_ours = False
        self.last_fetch_time = None

    def __str__(self):
        return "chunkid: %s, verified: %s, is_ours: %s" % (chunkid_to_hex(self.chunkid),
                                                           self.verified, self.is_ours)


_chunkmanager = None


def get_chunkmanager():
    global _chunkmanager
    if not _chunkmanager:
        _chunkmanager = ChunkManager()
    return _chunkmanager


class ChunkManager:
    def __init__(self):
        # initialize logger
        # IMPORTANT: we must ALWAYS use self.__logger.* for logging and not logging.*,
        # since we need instance-level logging
        self.__logger = initlogging('', __name__)

        # the actual storage layer
        self.__storage = ChunkStorage(os.path.join(basedir, "chunkdata"), mode=0o0700)

        # tmp storage
        self.__tmpstorage = ChunkStorage(os.path.join(basedir, "tmpstorage"), mode=0o0700)

    def index_temp_storage(self):
        return self.__tmpstorage.index()

    def move_to_persistant_storage(self, chunk_id):
        chunk_data = self.__tmpstorage.get(chunk_id)
        self.__storage.put(chunk_id, chunk_data)
        self.__tmpstorage.delete(chunk_id)


class ChunkManagerOld:
    def __init__(self, aliasmanager):
        # initialize logger
        # IMPORTANT: we must ALWAYS use self.__logger.* for logging and not logging.*,
        # since we need instance-level logging
        self.__logger = initlogging('', __name__)

        # the actual storage layer
        self.__storagedir = os.path.join(basedir, "chunkdata")
        self.__storage = ChunkStorage(self.__storagedir, mode=0o0700)

        # alias manager
        self.__alias_manager = aliasmanager

        # databases we keep
        # FIXME: as we have sqlite DB with Chunk table - we dont' need this. Remove carefully.
        self.__chunk_db = {}
        self.__missing_chunks = {}

        # tmp storage
        self.__tmpstoragedir = os.path.join(basedir, "tmpstorage")
        self.__tmpstorage = ChunkStorage(self.__tmpstoragedir, mode=0o0700)

        # run other initializations
        self.__initialize()

    def __initialize(self):
        self.__logger.debug("Initializing")

        # initializations
        self.__recalculate_ownership_of_all_chunks()
        self.__verify_all_files_on_disk()
        # self.__purge_orphaned_storage_entries()
        # self.__purge_orphaned_files()

    def __verify_all_files_on_disk(self):
        self.__logger.debug("Verifying local files in %s" % self.__storagedir)

        # reads the filesystem and fills our DB of chunks we have
        for chunkid in self.__storage.index():
            if not self.__storage.verify(chunkid):
                self.__logger.warning("Verify failed for local file at boot, deleting: %s" % chunkid_to_hex(chunkid))
                self.__storage.delete(chunkid)

    def __recalculate_ownership_of_all_chunks(self):
        for chunk, chunkid in self.__chunk_db.items():
            self.__update_chunk_ownership(chunk)

    def __update_chunk_ownership(self, chunk):
        # if even a single alias says we own this chunk, we do
        actual_chunk_is_ours = self.__alias_manager.we_own_chunk(chunk.chunkid)

        if actual_chunk_is_ours:
            # maintain file db
            # self.__logger.debug("Chunk %s is now OWNED" % chunkid_to_hex(chunk.chunkid))
            chunk.is_ours = True

            # fetch if missing
            if not chunk.verified:
                self.__fetch_chunk_locally_or_mark_missing(chunk)
        else:
            # self.__logger.debug("Chunk %s is now DISOWNED" % chunkid_to_hex(chunk.chunkid))
            chunk.is_ours = False

            # TODO: we can purge chunk if we no longer need it

        return actual_chunk_is_ours

    def __mark_chunk_as_missing(self, chunk):
        # self.__logger.warning("Chunk %s missing, added to todolist" % chunkid_to_hex(chunk.chunkid))
        chunk.verified = False
        self.__missing_chunks[chunk.chunkid] = chunk

    def __store_missing_chunk(self, chunk, data):
        # store chunk
        self.__storage.put(chunk.chunkid, data)
        chunk.verified = True

        if self.__missing_chunks.get(chunk.chunkid) is not None:
            del self.__missing_chunks[chunk.chunkid]

        # self.__logger.debug("Chunk %s is loaded" % chunkid)

    def __fetch_chunk_locally_or_mark_missing(self, chunk):
        # if we don't have it or it's not verified for some reason, fetch it
        if not chunk.verified:
            data = None

            # do we have it locally? - this can happen if we just booted up
            if self.__storage.verify(chunk.chunkid):
                # self.__logger.debug("Found chunk %s locally" % chunkid_to_hex(chunk.chunkid))
                data = self.__storage.get(chunk.chunkid)

            # do we have it in tmp storage?
            if data is None:
                if self.__tmpstorage.verify(chunk.chunkid):
                    data = self.__tmpstorage.get(chunk.chunkid)
                    # self.__logger.debug("Found chunk %s in temporary storage" % chunkid_to_hex(chunk.chunkid))

            # did we find the data?
            if data is not None:
                self.__store_missing_chunk(chunk, data)
            else:
                # we need to fetch the chunk using RPC
                self.__mark_chunk_as_missing(chunk)

    def __purge_orphaned_storage_entries(self):
        self.__logger.info("Purging orphaned files")
        for chunkid, chunk in self.__chunk_db.items():
            if not chunk.is_ours or not chunk.verified:
                self.__storage.delete(chunkid)

    def __purge_orphaned_files(self):
        self.__logger.debug("Purging local files in %s" % self.__storagedir)

        # reads the filesystem and fills our DB of chunks we have
        for chunkid in self.__storage.index():
            chunk = self.__chunk_db.get(chunkid)

            if chunk is None:
                # we don't know what this file is (perhaps it used to belong to us but not anymore)
                self.__storage.delete(chunkid)

        self.__logger.debug("Discovered %s files in local storage" % len(self.__chunk_db))

    def __get_or_create_chunk(self, chunkid):
        created = False
        if self.__chunk_db.get(chunkid) is None:
            created = True
            self.__chunk_db[chunkid] = Chunk(chunkid=chunkid)

        chunk = self.__chunk_db[chunkid]
        return created, chunk

    # START - CHUNK FETCHER
    def get_missing_chunks_num(self):
        return len(self.__missing_chunks)

    def get_random_missing_chunks(self, sample_size):
        now = dt.now()

        missing_chunks = []
        for chunkid, chunk in self.__missing_chunks.items():
            # if chunk has been fetched previously
            if chunk.last_fetch_time is not None:
                # and CHUNK_REFETCH_INTERVAL seconds have elapsed since
                elapsed = (now - chunk.last_fetch_time).total_seconds()
                if elapsed < NetWorkSettings.CHUNK_REFETCH_INTERVAL:
                    self.__logger.debug("Not refetching chunk: %s, elapsed: %s" % (chunkid_to_hex(chunkid), elapsed))
                    continue

            missing_chunks.append(chunkid)

        # If sample size is less than the missing chunk list, we return it all. random.sample() errors out
        # when sample_size < len(items). This also conveniently handles the case when the list is empty
        if len(missing_chunks) <= sample_size:
            return missing_chunks
        else:
            return random.sample(missing_chunks, sample_size)

    def failed_to_fetch_chunk(self, chunkid):
        chunk = self.__chunk_db.get(chunkid)
        if chunk is None:
            # seems like this chunk got deleted while we were fetching it
            return
        self.__logger.warning("Failed to fetch chunk %s" % chunkid_to_hex(chunkid))
        chunk.last_fetch_time = dt.now()

    def store_missing_chunk(self, chunkid, data):
        chunk = self.__chunk_db.get(chunkid)
        if chunk is None:
            # seems like this chunk got deleted while we were fetching it
            return

        self.__store_missing_chunk(chunk, data)

    # END - CHUNK FETCHER

    def select_random_chunks_we_have(self, n):
        chunks_we_have = []
        for chunk_id, chunk in self.__chunk_db.items():
            if chunk.verified and chunk.is_ours:
                chunks_we_have.append(chunk)

        if len(chunks_we_have) == 0:
            # we have no chunks yet
            return []

        return random.sample(chunks_we_have, n)

    def update_mn_list(self, added, removed):
        if len(added) + len(removed) > 0:
            if get_blockchain_connection().pastelid in removed:
                # TODO: figure out what to do here
                self.__logger.warning("I am removed from the MN list, aborting %s" % get_blockchain_connection().pastelid)
                # return

            self.__logger.info("MN list has changed -> added: %s, removed: %s" % (added, removed))
            self.dump_internal_stats("DB STAT Before")
            self.__recalculate_ownership_of_all_chunks()
            # self.__purge_orphaned_storage_entries()
            # self.__purge_orphaned_db_entries()
            self.dump_internal_stats("DB STAT After")

    def add_new_chunks(self, chunks):
        # self.dump_internal_stats("DB STAT Before")
        for chunkid in chunks:
            created, chunk = self.__get_or_create_chunk(chunkid)
            self.__update_chunk_ownership(chunk)
        # self.dump_internal_stats("DB STAT After")

    def store_chunk_in_temp_storage(self, chunkid, data):
        if chunkid != get_pynode_digest_int(data):
            raise ValueError("data does not match chunkid!")

        self.__tmpstorage.put(chunkid, data)

    def get_chunk_if_we_have_it(self, chunkid):
        # if not self.__alias_manager.we_own_chunk(chunkid):
        #     raise ValueError("We don't own this chunk!")
        self.__logger.warn('Chunk DB dump')
        self.__logger.warn('{}'.format(self.__chunk_db))
        chunk = self.__chunk_db.get(chunkid)
        if chunk is None:
            self.__logger.info(
                "This chunk is missing from our database, is it in any valid tickets? {}".format(chunkid))
            return None

        return self.get_chunk(chunk)

    def get_chunk(self, chunk_id):
        # try to find chunk in chunkstorage
        # if chunk.verified:
        #     return self.__storage.get(chunk.chunkid)

        # fall back to try and find chunk in tmpstorage
        #  - for tickets that are registered through us, but not final on the blockchain yet, this is how we bootstrap
        #  - we are also graceful and can return chunks that are not ours...
        if self.__tmpstorage.verify(chunk_id):
            return self.__tmpstorage.get(chunk_id)

        # we have failed to find the chunk, mark it as missing
        # self.__mark_chunk_as_missing(chunk)

    # DEBUG FUNCTIONS
    def dump_internal_stats(self, msg=""):
        if msg == "":
            prefix = ""
        else:
            prefix = "%s -> " % msg
        tried_fetch_but_failed = [x.chunkid for x in self.__missing_chunks.values() if x.last_fetch_time is not None]
        self.__logger.debug("%schunk_db: %s, missing_chunks: %s, failed_fetch: %s" % (
            prefix, len(self.__chunk_db), len(self.__missing_chunks), len(tried_fetch_but_failed)))

    def dump_file_db(self):
        for k, v in self.__chunk_db.items():
            self.__logger.debug("FILE %s: %s" % (chunkid_to_hex(k), v))
            self.__storage.get(k)
    # END
