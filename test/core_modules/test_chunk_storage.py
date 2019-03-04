import os
import stat
import random
import unittest
import shutil
import tempfile

from core_modules.chunk_storage import ChunkStorage
from core_modules.helpers import get_pynode_digest_int


class TestChunkStorageInit(unittest.TestCase):
    def test_chunkstorage_creation_umask(self):
        test_dir = tempfile.mkdtemp()
        shutil.rmtree(test_dir)
        ChunkStorage(test_dir, mode=0o0700)
        dirstat = os.stat(test_dir)
        permissions = stat.filemode(dirstat.st_mode)
        self.assertEqual(permissions, "drwx------")


class TestChunkStorageInterface(unittest.TestCase):
    def setUp(self):
        CHUNK_SIZE = 1024 * 1024

        random.seed(236823823)
        self.chunk_data = random.getrandbits(CHUNK_SIZE * 8).to_bytes(CHUNK_SIZE, byteorder="big")
        self.chunk_digest = get_pynode_digest_int(self.chunk_data)

        self.test_dir = tempfile.mkdtemp()
        self.cs = ChunkStorage(self.test_dir, mode=0o0700)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_invalid_chunkname_type(self):
        with self.assertRaises(TypeError):
            self.cs.get("test")

    def test_short_chunkname(self):
        with self.assertRaises(FileNotFoundError):
            self.cs.get(1)

    def test_put_get(self):
        self.cs.put(self.chunk_digest, self.chunk_data)
        data = self.cs.get(self.chunk_digest)
        self.assertEqual(self.chunk_data, data)

    def test_get_offset(self):
        self.cs.put(self.chunk_digest, self.chunk_data)
        data = self.cs.get(self.chunk_digest, offset=1000, length=20)
        self.assertEqual(data, b'.na\x8e\x86\xf6\n\xf7)\xbbH\xf5p{\xe4g\x99\x8b\x88\r')

    def test_get_nosuchfile(self):
        with self.assertRaises(FileNotFoundError):
            self.cs.get(123456789)

    def test_delete(self):
        self.cs.put(self.chunk_digest, self.chunk_data)
        self.cs.delete(self.chunk_digest)
        with self.assertRaises(FileNotFoundError):
            self.cs.get(self.chunk_digest)

    def test_exists(self):
        self.cs.put(self.chunk_digest, self.chunk_data)
        self.assertTrue(self.cs.exists(self.chunk_digest))

    def test_exists_nosuchfile(self):
        self.assertFalse(self.cs.exists(213697237))

    def test_verify(self):
        self.cs.put(self.chunk_digest, self.chunk_data)
        self.assertTrue(self.cs.verify(self.chunk_digest))

    def test_verify_corrupted_file(self):
        self.cs.put(self.chunk_digest, b'random data')
        self.assertFalse(self.cs.verify(self.chunk_digest))

    def test_index(self):
        self.cs.put(self.chunk_digest, self.chunk_data)
        self.assertListEqual([self.chunk_digest], list(self.cs.index()))
