"""
Storage management (filesystem paths, more or less high level methods).
"""

from core_modules.helpers import get_pynode_digest_int
from core_modules.chunk_storage import ChunkStorage
from core_modules.logger import get_logger
from core_modules.settings import Settings

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
        self.__logger = get_logger('Chunk Manager')

        # the actual storage layer
        self.__logger.debug("Setting ChunkStorage at %s" % Settings.CHUNK_DATA_DIR)
        self.__storage = ChunkStorage(Settings.CHUNK_DATA_DIR, mode=0o0700)

        # tmp storage
        self.__logger.debug("Setting TmpStorage at %s" % Settings.TEMP_STORAGE_DIR)
        self.__tmpstorage = ChunkStorage(Settings.TEMP_STORAGE_DIR, mode=0o0700)

        self.__logger.debug("Chunk Manager initialized")

    def get_storage_path(self):
        return self.__storage.get_basedir_path()

    def get_tmp_storage_path(self):
        return self.__tmpstorage.get_basedir_path()

    def index_temp_storage(self):
        return self.__tmpstorage.index()

    def index_storage(self):
        return self.__storage.index()

    def rm_from_temp_storage(self, chunk_id):
        self.__tmpstorage.delete(chunk_id)

    def move_to_persistant_storage(self, chunk_id):
        chunk_data = self.__tmpstorage.get(chunk_id)
        self.__storage.put(chunk_id, chunk_data)
        self.__tmpstorage.delete(chunk_id)

    def store_chunk_in_temp_storage(self, chunkid, data):
        """
        :param chunkid: integer
        :param data: bytes
        """
        if chunkid != get_pynode_digest_int(data):
            raise ValueError("data does not match chunkid!")

        self.__tmpstorage.put(chunkid, data)

    def store_chunk_in_storage(self, chunkid, data):
        """
        :param chunkid: integer
        :param data: bytes
        """
        if chunkid != get_pynode_digest_int(data):
            raise ValueError("data does not match chunkid!")

        self.__storage.put(chunkid, data)

    def get_chunk_data(self, chunk_id):
        # try to find chunk in chunkstorage
        return self.__storage.get(chunk_id)
