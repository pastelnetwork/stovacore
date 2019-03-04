import unittest

from core_modules.blackbox_modules.compression import compress, decompress


class TestCompression(unittest.TestCase):
    def test_compression(self):
        data = b'X' * 1024 * 1024
        compressed = compress(data)
        decompressed = decompress(compressed)
        self.assertEqual(data, decompressed)
