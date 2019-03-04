import time
import unittest

from test.helpers import Daemon


class TestBlockChain(unittest.TestCase):
    def setUp(self):
        self.daemon = Daemon("rt", "rt", 10011, "127.0.0.1", 10012)
        self.daemon.start()
        self.blockchain = self.daemon.connect()

    def tearDown(self):
        self.daemon.stop()

    def test_blockchain_storage(self):
        # generate some coins
        self.blockchain.generate(100)
        self.blockchain.generate(100)

        origdata = b'THIS IS SOME TEST DATA'
        txid = self.blockchain.store_data_in_utxo(origdata)
        retdata = self.blockchain.retrieve_data_from_utxo(txid)
        self.assertEqual(origdata, retdata)

    def test_generate(self):
        for i in range(3):
            self.blockchain.generate(1)
            time.sleep(1)

    def test_search_chain(self):
        # generate some coins
        self.blockchain.generate(200)

        data = b'TEST DATA'
        txid = self.blockchain.store_data_in_utxo(data)
        self.blockchain.generate(15)

        txids = [txid for txid in self.blockchain.search_chain(confirmations=0)]
        self.assertIn(txid, txids)
