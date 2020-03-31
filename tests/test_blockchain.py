"""
This module contain system test, which require some setup:
 - Local cNode
 - A testnet with minimum 10 valid masternodes
 - Registered pastelID for local cNode
 - Working internet conection.
"""
import json
import unittest
import os
import asyncio
import random
from cnode_connection import get_blockchain_connection
from core_modules.ticket_models import RegistrationTicket
from utils.mn_ordering import get_masternode_ordering

PASTELID = 'jXaQj8FA9FGP6KzKNKz9bPEX7owTWqF7CeQ2Vy1fT21pEMUeveqBf6DXhRv3o6mBN3AX5bBcTuvafDcepkZ3wp'
PASSPHRASE = 'taksa'

TXID_LENGTH = 64


class BlockchainInteractionTestCase(unittest.TestCase):
    def setUp(self):
        # fill this with created pastelID (should be registered) and passphrase
        os.environ.setdefault('PASTEL_ID', PASTELID)
        os.environ.setdefault('PASSPHRASE', PASSPHRASE)

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


class ImageRegistrationTestCase(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault('PASTEL_ID', PASTELID)
        os.environ.setdefault('PASSPHRASE', PASSPHRASE)

    def test_get_ticket(self):
        # list act tickets
        result = get_blockchain_connection().list_tickets("act")
        act_ticket_txids = list(filter(lambda x: len(x) == TXID_LENGTH, result))

        txid = act_ticket_txids[0]

        # get ticket by txid
        ticket = json.loads(get_blockchain_connection().get_ticket(txid))
        regticket_base64 = ticket['ticket']['art_ticket']

        regticket = RegistrationTicket(serialized_base64=regticket_base64)
        self.assertEqual(regticket.blocknum, 4494)
