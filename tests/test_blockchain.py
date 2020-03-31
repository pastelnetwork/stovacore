import unittest
import os
import asyncio
import random
from cnode_connection import get_blockchain_connection
from utils.mn_ordering import get_masternode_ordering


class BlockchainInteractionTestCase(unittest.TestCase):
    def setUp(self):
        # fill this with created pastelID (should be registered) and passphrase
        os.environ.setdefault('PASTEL_ID', 'jXaQj8FA9FGP6KzKNKz9bPEX7owTWqF7CeQ2Vy1fT21pEMUeveqBf6DXhRv3o6mBN3AX5bBcTuvafDcepkZ3wp')
        os.environ.setdefault('PASSPHRASE', 'taksa')

    def test_masternode_top(self):
        workers = get_blockchain_connection().masternode_top(None)
        print(len(workers))
        for node in workers:
            self.assertIn('extKey', node)
            self.assertIn('extAddress', node)

    def test_mn_ordering(self):
        async def send_ping(rpc_client):
            msg = bytes(''.join(random.choice('abcdef') for x in range(4)), 'utf8')
            response = await rpc_client.send_rpc_ping(msg)
            self.assertEqual(response, msg)

        rpc_clients = get_masternode_ordering()

        self.assertEqual(len(rpc_clients), 3)
        # test each client response to ping request
        for client in rpc_clients:
            asyncio.run(send_ping(client))
