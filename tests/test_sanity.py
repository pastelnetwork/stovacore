import unittest

from pynode.masternode_daemon import MasterNodeDaemon


class TestSystemStarts(unittest.TestCase):
    def setUp(self):
        pass

    def test_create_masternodedaemon_obj(self):
        daemon = MasterNodeDaemon()
