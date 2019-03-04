import unittest

from core_modules.blackbox_modules import luby


class TestLuby(unittest.TestCase):
    def test_luby_decode_encoded(self):
        redundancy_factor = 2
        block_size = 1024

        data = b'A' * 1024 * 512 + b'A' * 100  # test for padding
        blocks = luby.encode(redundancy_factor, block_size, data)
        decoded = luby.decode(blocks)
        self.assertEqual(data, decoded)
