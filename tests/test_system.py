"""
This module contain system test, which require some setup:
 - Local cNode
 - A testnet with minimum 10 valid masternodes
 - Registered pastelID for local cNode
 - Working internet conection.

This test are actually not 'refined' tests - they depend on the testnet state.
Consider it more like manual test which are upgraded with a bit of automation.
"""
import json
import logging
import unittest
import os
import asyncio
import random

from cnode_connection import get_blockchain_connection
from core_modules.database import MASTERNODE_DB, DB_MODELS, Masternode, ChunkMnDistance, ChunkMnRanked, Chunk, \
    ActivationTicket
from core_modules.rpc_client import RPCClient
from core_modules.rpc_serialization import RPCMessage
from core_modules.ticket_models import RegistrationTicket
from pynode.tasks import TXID_LENGTH, update_masternode_list, refresh_masternode_list, index_new_chunks, \
    get_and_proccess_new_activation_tickets
from utils.mn_ordering import get_masternode_ordering
from cnode_connection import reset_blockchain_connection

CLIENT_PASTELID = 'jXaQj8FA9FGP6KzKNKz9bPEX7owTWqF7CeQ2Vy1fT21pEMUeveqBf6DXhRv3o6mBN3AX5bBcTuvafDcepkZ3wp'
SERVER_PASTELID = 'jXaSNRnSiPkz4BettdvJvmgKAFkfQvu4kFrcsRJcsFaBYiMJxo7zrvftPE2bcYGiViW5YLAuiALrtpoD1QbJ39'
PASSPHRASE = 'taksa'


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


class MasternodeFetcherTaskTestCase(unittest.TestCase):
    def setUp(self):
        # warnings.simplefilter('ignore')
        switch_pastelid(CLIENT_PASTELID, PASSPHRASE)
        MASTERNODE_DB.init(':memory:')
        MASTERNODE_DB.connect(reuse_if_open=True)
        MASTERNODE_DB.create_tables(DB_MODELS)

    def test_masternode_fetcher_task(self):
        self.assertEqual(Masternode.select().count(), 0)
        update_masternode_list()
        masternodes = list(Masternode.select())
        # update with actual amount of masternodes in the network
        self.assertEqual(len(masternodes), 7)

    def test_masternodes_refresh_task_with_no_chunks(self):
        self.assertEqual(Masternode.select().count(), 0)
        self.assertEqual(ChunkMnDistance.select().count(), 0)
        self.assertEqual(ChunkMnRanked.select().count(), 0)
        refresh_masternode_list()
        self.assertEqual(Masternode.select().count(), 7)
        self.assertEqual(ChunkMnDistance.select().count(), 0)
        self.assertEqual(ChunkMnRanked.select().count(), 0)

    def test_masternodes_refresh_task_with_chunks(self):
        # TODO: add chunks
        self.assertEqual(Masternode.select().count(), 0)
        self.assertEqual(ChunkMnDistance.select().count(), 0)
        self.assertEqual(ChunkMnRanked.select().count(), 0)
        refresh_masternode_list()
        self.assertEqual(Masternode.select().count(), 7)
        self.assertEqual(ChunkMnDistance.select().count(), 10)  # FIXME: replace with real values
        self.assertEqual(ChunkMnRanked.select().count(), 10)  # FIXME: replace with real values


class ProcessNewActTicketsTestCase(unittest.TestCase):
    def setUp(self):
        # warnings.simplefilter('ignore')
        switch_pastelid(CLIENT_PASTELID, PASSPHRASE)
        MASTERNODE_DB.init(':memory:')
        MASTERNODE_DB.connect(reuse_if_open=True)
        MASTERNODE_DB.create_tables(DB_MODELS)

    def test_process_new_act_tickets(self):
        """
        Outputs: In the database - Chunk, ActivationTicket instances created.
        """
        self.assertEqual(Chunk.select().count(), 0)
        self.assertEqual(ActivationTicket.select().count(), 0)
        get_and_proccess_new_activation_tickets()
        chunks = list(Chunk.select())
        act_tickets = list(ActivationTicket.select())
        # FIXME: validate actual number of chunks/act tickets on the blockchain
        self.assertEqual(Chunk.select().count(), 16)
        self.assertEqual(ActivationTicket.select().count(), 4)


class IndexNewChunksTaskTestCase(unittest.TestCase):
    def setUp(self):
        # warnings.simplefilter('ignore')
        switch_pastelid(CLIENT_PASTELID, PASSPHRASE)
        MASTERNODE_DB.init(':memory:')
        MASTERNODE_DB.connect(reuse_if_open=True)
        MASTERNODE_DB.create_tables(DB_MODELS)

    def test_index_new_chunks(self):
        self.assertEqual(Chunk.select().count(), 0)
        self.assertEqual(Masternode.select().count(), 0)
        self.assertEqual(ChunkMnDistance.select().count(), 0)
        self.assertEqual(ChunkMnRanked.select().count(), 0)
        refresh_masternode_list()
        self.assertEqual(ChunkMnDistance.select().count(), 0)
        self.assertEqual(ChunkMnRanked.select().count(), 0)
        self.assertEqual(Masternode.select().count(), 7)
        get_and_proccess_new_activation_tickets()
        self.assertEqual(Chunk.select().count(), 16)
        self.assertEqual(ActivationTicket.select().count(), 4)
        for chunk in Chunk.select():
            self.assertEqual(chunk.indexed, False)
            self.assertEqual(chunk.confirmed,
                             True)  # since we received chunk info from activation ticket - it's confirmed.
        index_new_chunks()
        for chunk in Chunk.select():
            self.assertEqual(chunk.indexed, True)
            self.assertEqual(chunk.confirmed, True)
        chunk_mn_distance = list(ChunkMnDistance.select())
        chunk_mn_ranked = list(ChunkMnRanked.select())
        self.assertEqual(ChunkMnDistance.select().count(), Masternode.select().count()*Chunk.select().count())
        self.assertEqual(ChunkMnRanked.select().count(), Masternode.select().count()*Chunk.select().count())
        # verify ranks generated
        ranks = set()
        for cmnr in ChunkMnRanked.select():
            ranks.add(cmnr.rank)
        self.assertEqual(len(ranks), 7)
        print('Ranks : {}'.format(ranks))


class FetchChunkTestCase(unittest.TestCase):
    def setUp(self):
        # warnings.simplefilter('ignore')
        switch_pastelid(CLIENT_PASTELID, PASSPHRASE)
        MASTERNODE_DB.init(':memory:')
        MASTERNODE_DB.connect(reuse_if_open=True)
        MASTERNODE_DB.create_tables(DB_MODELS)
        # logging.basicConfig(level=logging.DEBUG)

    def test_fetch_chunk_rpc(self):
        # TODO: find out which node has a given chunk (has stored = True in internal DB).
        pass
        # async def fetch_chunk(rpc_client, id):
        #     response = await rpc_client.send_rpc_fetchchunk(id)
        #     if response is not None:
        #         from pdb import set_trace; set_trace()
        #         print('Received something!')
        #
        # refresh_masternode_list()
        # get_and_proccess_new_activation_tickets()
        # # at this point Chunk db records should exist
        # masternodes = list(Masternode.select())
        # chunks = list(Chunk.select())
        # for m in range(len(masternodes)):
        #     for c in range(len(chunks)):
        #         print("fetchin chunk for mn {} chunk {}".format(m, c))
        #         client = masternodes[m].get_rpc_client()
        #         asyncio.run(fetch_chunk(client, chunks[c].chunk_id))
        # # client = masternodes[0].get_rpc_client()
        # # asyncio.run(fetch_chunk(client, chunks[6].chunk_id))
