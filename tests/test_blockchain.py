"""
This module contain system test, which require some setup:
 - Local cNode
 - A testnet with minimum 10 valid masternodes
 - Registered pastelID for local cNode
 - Working internet conection.
"""
import base64
import json
import unittest
import os
import asyncio
import random
import logging

from cnode_connection import get_blockchain_connection
from core_modules.rpc_client import RPCClient
from core_modules.rpc_serialization import RPCMessage
from core_modules.ticket_models import RegistrationTicket
from utils.mn_ordering import get_masternode_ordering
from cnode_connection import reset_blockchain_connection

CLIENT_PASTELID = 'jXaQj8FA9FGP6KzKNKz9bPEX7owTWqF7CeQ2Vy1fT21pEMUeveqBf6DXhRv3o6mBN3AX5bBcTuvafDcepkZ3wp'
SERVER_PASTELID = 'jXaSNRnSiPkz4BettdvJvmgKAFkfQvu4kFrcsRJcsFaBYiMJxo7zrvftPE2bcYGiViW5YLAuiALrtpoD1QbJ39'
PASSPHRASE = 'taksa'

TXID_LENGTH = 64


def switch_pastelid(pastelid: str, passphrase: str):
    """
    To emulate situation when we're now on another node and using another pastelID.
    """
    reset_blockchain_connection()
    os.environ['PASTEL_ID'] = pastelid
    os.environ['PASSPHRASE'] = passphrase


class BlockchainInteractionTestCase(unittest.TestCase):
    def setUp(self):
        # fill this with created pastelID (should be registered) and passphrase
        os.environ.setdefault('PASTEL_ID', CLIENT_PASTELID)
        os.environ.setdefault('PASSPHRASE', PASSPHRASE)
        # logging.basicConfig(level=logging.DEBUG)

    def test_masternode_top(self):
        workers = get_blockchain_connection().masternode_top(None)
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
        os.environ.setdefault('PASTEL_ID', CLIENT_PASTELID)
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


class PastelSignVerifyTestCase(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault('PASTEL_ID', CLIENT_PASTELID)
        os.environ.setdefault('PASSPHRASE', PASSPHRASE)

    def test_sign_verify(self):
        data = b'some data'
        signature = get_blockchain_connection().pastelid_sign(data)
        result = get_blockchain_connection().pastelid_verify(data, signature, CLIENT_PASTELID)
        self.assertEqual(result, True)
        result = get_blockchain_connection().pastelid_verify(data, 'aaa', CLIENT_PASTELID)
        self.assertEqual(result, False)


class RPCClientTestCase(unittest.TestCase):
    def setUp(self):
        # fill this with created pastelID (should be registered) and passphrase
        switch_pastelid(CLIENT_PASTELID, PASSPHRASE)
        # logging.basicConfig(level=logging.DEBUG)
        self.rpc_client = RPCClient(SERVER_PASTELID, '127.0.0.1', '4444')

    def test_generate_reconstruct_request_packet(self):
        msg = ['taksa']
        self.assertRaises(ValueError, self.rpc_client.generate_packet, 'string')
        self.assertRaises(ValueError, self.rpc_client.generate_packet, {'dict': 'dict'})
        request_packet = self.rpc_client.generate_packet(msg)
        self.assertEqual(type(request_packet), bytes)

        switch_pastelid(SERVER_PASTELID, PASSPHRASE)
        rpc_message = RPCMessage.reconstruct(request_packet)
        sender_id, received_msg = rpc_message.sender_id, rpc_message.data
        self.assertEqual(sender_id, CLIENT_PASTELID)
        self.assertEqual(received_msg, msg)

    def test_rpcmessage_sign_verify(self):
        m = RPCMessage(['taksa'], CLIENT_PASTELID)
        m.sign()
        self.assertTrue(m.verify())

    def test_pastelid_switch(self):
        self.assertEqual(get_blockchain_connection().pastelid, CLIENT_PASTELID)
        switch_pastelid(SERVER_PASTELID, PASSPHRASE)
        self.assertEqual(get_blockchain_connection().pastelid, SERVER_PASTELID)

    def test_reconstruct(self):
        data = ['taksa']
        m = RPCMessage(data, SERVER_PASTELID)
        packed = m.pack()

        switch_pastelid(SERVER_PASTELID, PASSPHRASE)

        m1 = RPCMessage.reconstruct(packed)
        self.assertDictEqual(m.container, m1.container)
        self.assertTrue(m1.verify())
        self.assertEqual(m1.container['sender_id'], CLIENT_PASTELID)
        self.assertEqual(m1.container['data'], data)

    def test_reconstruct_wrong_recipient(self):
        m = RPCMessage(['taksa'], 'some other pastelid')
        packed = m.pack()

        switch_pastelid(SERVER_PASTELID, PASSPHRASE)

        self.assertRaises(ValueError, RPCMessage.reconstruct, packed)
