import unittest

from unittest.mock import patch

from pynode.masternode_daemon import MasterNodeDaemon
from wallet.pastel_client import PastelClient


class TestSystemStarts(unittest.TestCase):
    @patch('pynode.masternode_daemon.RPCServer', autospec=True)
    def test_create_masternodedaemon_obj(self, rpc_server):
        daemon = MasterNodeDaemon()


class TestClientSanity(unittest.TestCase):
    def test_pastel_client_starts(self):
        pastel_client = PastelClient('pastelid', 'passphrase')
