import os

from core_modules.helpers import get_pynode_digest_int
from .helpers import chunkid_to_hex, hex_to_chunkid


class ChunkStorage:
    def __init__(self, basedir, mode):
        self.__basedir = basedir
        self.__basedir_umask = mode

        self.__init_basedir()

    def __init_basedir(self):
        os.makedirs(self.__basedir, mode=self.__basedir_umask, exist_ok=True)

    def __derive_fs_file_name(self, chunkname):
        if type(chunkname) != int:
            raise TypeError("Chunkname must be int!")

        # convert integer to filename in hex
        hexchunkname = chunkid_to_hex(chunkname)

        # max 4096 level 1 dirs, containing max 4096 level2 dirs, containing files
        dir1 = hexchunkname[0:3]
        dir2 = hexchunkname[3:6]
        filename = hexchunkname

        directory_name = os.path.join(self.__basedir, dir1, dir2)
        fs_file_name = os.path.join(self.__basedir, dir1, dir2, filename)

        return directory_name, fs_file_name

    def get(self, chunkname, offset=0, length=-1):
        dirname, filename = self.__derive_fs_file_name(chunkname)

        with open(filename, "rb") as f:
            f.seek(offset)
            return f.read(length)

    def put(self, chunkname, data):
        dirname, filename = self.__derive_fs_file_name(chunkname)

        os.makedirs(dirname, mode=self.__basedir_umask, exist_ok=True)

        with open(filename, "wb") as f:
            f.write(data)

    def delete(self, chunkname):
        dirname, filename = self.__derive_fs_file_name(chunkname)

        try:
            os.unlink(filename)
        except FileNotFoundError:
            pass

        # TODO: clean up directories that became empty

    def exists(self, chunkname):
        dirname, filename = self.__derive_fs_file_name(chunkname)

        try:
            os.stat(filename)
        except FileNotFoundError:
            return False
        else:
            return True

    def verify(self, chunkname):
        try:
            data = self.get(chunkname)
        except FileNotFoundError:
            return False

        digest = get_pynode_digest_int(data)
        return chunkname == digest

    def index(self):
        for dir1 in os.scandir(self.__basedir):
            for dir2 in os.scandir(os.path.join(self.__basedir, dir1.name)):
                for dirent in os.scandir(os.path.join(self.__basedir, dir1.name, dir2.name)):
                    fullpath = os.path.join(dir1, dir2, dirent.name)

                    if dirent.is_file():
                        yield hex_to_chunkid(dirent.name)
                    else:
                        raise ValueError("Invalid entity found in filesystem, not file or directory: %s" % fullpath)
