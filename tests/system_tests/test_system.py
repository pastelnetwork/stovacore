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
import shutil
import unittest
import os
import asyncio
import random
from pprint import pprint

from cnode_connection import get_blockchain_connection
from core_modules.chunkmanager import get_chunkmanager
from core_modules.database import MASTERNODE_DB, DB_MODELS, Masternode, ChunkMnDistance, ChunkMnRanked, Chunk, \
    ActivationTicket
from core_modules.rpc_client import RPCClient
from core_modules.rpc_serialization import RPCMessage
from core_modules.ticket_models import RegistrationTicket
from pynode.tasks import TXID_LENGTH, update_masternode_list, refresh_masternode_list, index_new_chunks, \
    get_and_proccess_new_activation_tickets, fetch_single_chunk_via_rpc, chunk_fetcher_task_body
from utils.mn_ordering import get_masternode_ordering
from cnode_connection import reset_blockchain_connection

CLIENT_PASTELID = 'jXZaYVHWw6czQ7r7oMHJkLjYDs7oSR4KWuSk3PybsWFnR2cjvjVpTMgQc7R2mfqT8eiggCwZb6SiHYRi7FouGh'
SERVER_PASTELID = 'jXXr3LQbBp7UN9CgmKQpbPJoEqPRBpuvwG4isEprjLymGujXGUsPS6KZmx3aq7B2Sk4HRaMmcRU9aYYovsokcL'

REAL_MN_PASTEL_ID = 'jXaHR8djB7VL6XFisRsGrv7P4fzna1wqdKMAJDHjhPgnh3kUdrRinv9yFowMivDEgAAU34bgm9u6hk98gE88CP'
PASSPHRASE = 'taksa'
MASTERNODE_NUMBER = 10  # number of masternodes in the network
CHUNK_NUMBER = 13  # number of chunks in the network
ACT_TICKET_NUMBER = 2  # number of art activation tickets in the network

# DISABLED_MASTERNODES = ['51.158.183.93:4444', '51.15.57.47:4444']
DISABLED_MASTERNODES = []


def disable_invalid_mns():
    Masternode.update(active=False).where(Masternode.ext_address << DISABLED_MASTERNODES).execute()


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
        self.assertEqual(regticket.blocknum, 3370)


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
        self.assertEqual(Masternode.get_active_nodes().count(), 0)
        update_masternode_list()
        masternodes = list(Masternode.get_active_nodes())
        # update with actual amount of masternodes in the network
        self.assertEqual(len(masternodes), MASTERNODE_NUMBER)

    def test_masternodes_refresh_task_with_no_chunks(self):
        self.assertEqual(Masternode.get_active_nodes().count(), 0)
        self.assertEqual(ChunkMnDistance.select().count(), 0)
        self.assertEqual(ChunkMnRanked.select().count(), 0)
        refresh_masternode_list()
        self.assertEqual(Masternode.get_active_nodes().count(), MASTERNODE_NUMBER)
        self.assertEqual(ChunkMnDistance.select().count(), 0)
        self.assertEqual(ChunkMnRanked.select().count(), 0)

    def test_masternodes_refresh_task_with_chunks(self):
        self.assertEqual(Masternode.get_active_nodes().count(), 0)
        self.assertEqual(ChunkMnDistance.select().count(), 0)
        self.assertEqual(ChunkMnRanked.select().count(), 0)
        get_and_proccess_new_activation_tickets()
        refresh_masternode_list()
        self.assertEqual(Masternode.get_active_nodes().count(), MASTERNODE_NUMBER)
        self.assertEqual(ChunkMnDistance.select().count(), MASTERNODE_NUMBER * CHUNK_NUMBER)
        self.assertEqual(ChunkMnRanked.select().count(), MASTERNODE_NUMBER * CHUNK_NUMBER)


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
        self.assertEqual(Chunk.select().count(), CHUNK_NUMBER)
        self.assertEqual(ActivationTicket.select().count(), ACT_TICKET_NUMBER)


class IndexNewChunksTaskTestCase(unittest.TestCase):
    def setUp(self):
        # warnings.simplefilter('ignore')
        switch_pastelid(CLIENT_PASTELID, PASSPHRASE)
        MASTERNODE_DB.init(':memory:')
        MASTERNODE_DB.connect(reuse_if_open=True)
        MASTERNODE_DB.create_tables(DB_MODELS)

    def test_index_new_chunks(self):
        self.assertEqual(Chunk.select().count(), 0)
        self.assertEqual(Masternode.get_active_nodes().count(), 0)
        self.assertEqual(ChunkMnDistance.select().count(), 0)
        self.assertEqual(ChunkMnRanked.select().count(), 0)
        refresh_masternode_list()
        self.assertEqual(ChunkMnDistance.select().count(), 0)
        self.assertEqual(ChunkMnRanked.select().count(), 0)
        self.assertEqual(Masternode.get_active_nodes().count(), MASTERNODE_NUMBER)
        get_and_proccess_new_activation_tickets()
        self.assertEqual(Chunk.select().count(), CHUNK_NUMBER)
        self.assertEqual(ActivationTicket.select().count(), 1)
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
        self.assertEqual(ChunkMnDistance.select().count(),
                         Masternode.get_active_nodes().count() * Chunk.select().count())
        self.assertEqual(ChunkMnRanked.select().count(), Masternode.get_active_nodes().count() * Chunk.select().count())
        # verify ranks generated
        ranks = set()
        for cmnr in ChunkMnRanked.select():
            ranks.add(cmnr.rank)
        self.assertEqual(len(ranks), MASTERNODE_NUMBER)
        print('Ranks : {}'.format(ranks))


class SQLRPCTestCase(unittest.TestCase):
    def setUp(self):
        switch_pastelid(CLIENT_PASTELID, PASSPHRASE)
        MASTERNODE_DB.init(':memory:')
        MASTERNODE_DB.connect(reuse_if_open=True)
        MASTERNODE_DB.create_tables(DB_MODELS)
        refresh_masternode_list()
        disable_invalid_mns()

    def test_sql_rpc(self):
        masternodes = list(Masternode.get_active_nodes())
        mn = masternodes[0].get_rpc_client()
        result = mn.send_rpc_execute_sql(
            'select artist_pk, created, localfee, is_valid_mn0, status, confirmed from regticket;');
        pprint(result)
        # self.assertEqual(len(result), 7)


class RPCPingAllNodesTestCase(unittest.TestCase):
    def setUp(self):
        # warnings.simplefilter('ignore')
        switch_pastelid(CLIENT_PASTELID, PASSPHRASE)
        MASTERNODE_DB.init(':memory:')
        MASTERNODE_DB.connect(reuse_if_open=True)
        MASTERNODE_DB.create_tables(DB_MODELS)
        refresh_masternode_list()
        disable_invalid_mns()

    def test_mn_ordering(self):
        async def send_ping(rpc_client):
            msg = bytes(''.join(random.choice('abcdef') for x in range(4)), 'utf8')
            response = await rpc_client.send_rpc_ping(msg)
            self.assertEqual(response, msg)
            print('{} ping OK'.format(rpc_client.server_ip))

        masternodes = Masternode.get_active_nodes()

        # test each client response to ping request
        for mn in masternodes:
            client = mn.get_rpc_client()
            asyncio.run(send_ping(client))


class FetchChunkTestCase(unittest.TestCase):
    def setUp(self):
        # warnings.simplefilter('ignore')
        switch_pastelid(CLIENT_PASTELID, PASSPHRASE)
        MASTERNODE_DB.init(':memory:')
        MASTERNODE_DB.connect(reuse_if_open=True)
        MASTERNODE_DB.create_tables(DB_MODELS)
        # logging.basicConfig(level=logging.DEBUG)
        refresh_masternode_list()
        disable_invalid_mns()
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def tearDown(self) -> None:
        # clear chunk storage
        storage_path = get_chunkmanager().get_storage_path()
        try:
            shutil.rmtree(storage_path)
        except FileNotFoundError:
            pass

    async def fetch_chunk(self, rpc_client, id):
        response = await rpc_client.send_rpc_fetchchunk(id)
        if response is not None:
            print('Received something!')
        else:
            print('fetch chunt returned None')

    async def fetch_chunk_which_exist(self, rpc_client, id):
        response = await rpc_client.send_rpc_fetchchunk(id)
        self.assertIsNotNone(response)

    async def fetch_chunk_which_does_not_exist(self, rpc_client, id):
        response = await rpc_client.send_rpc_fetchchunk(id)
        self.assertIsNone(response)

    @unittest.skip('test almost nothing')
    def test_fetch_all_chunks_from_all_mns(self):
        get_and_proccess_new_activation_tickets()
        self.assertNotEqual(Chunk.select().count(), 0)
        # at this point Chunk db records should exist
        masternodes = list(Masternode.get_active_nodes())
        chunks = list(Chunk.select())
        for m in range(len(masternodes)):
            for c in range(len(chunks)):
                print("fetchin chunk for mn {} chunk {}".format(m, c))
                client = masternodes[m].get_rpc_client()
                asyncio.run(self.fetch_chunk(client, chunks[c].chunk_id))
        # client = masternodes[0].get_rpc_client()
        # asyncio.run(fetch_chunk(client, chunks[6].chunk_id))

    def test_single_chunk_with_rpc_from_masternode(self):
        get_and_proccess_new_activation_tickets()
        # get a masternode which we know stores some chunks
        mn = Masternode.get_active_nodes()[0]
        client = mn.get_rpc_client()
        # get list of chunk this masternode stores
        chunks = client.send_rpc_execute_sql('select chunk_id from chunk where stored=true and confirmed=true;')
        chunk_ids_remote_mn_stores = [x['chunk_id'] for x in chunks]

        # get list of chunk this masternode does not store
        chunk_ids_remote_mn_doesnt_store = [c.chunk_id for c in
                                            Chunk.select().where(Chunk.chunk_id.not_in(chunk_ids_remote_mn_stores))]

        # check that masternode returns chunk data for all chunks it stores
        for c_id in chunk_ids_remote_mn_stores:
            asyncio.run(self.fetch_chunk_which_exist(client, c_id))

        # check that masternode returns None for chunks it does not stores
        for c_id in chunk_ids_remote_mn_doesnt_store:
            asyncio.run(self.fetch_chunk_which_does_not_exist(client, c_id))

    def test_fetch_chunk_with_mn_autoselect(self):
        chunks_received = 0
        chunks_failed = 0

        async def fetch_chunk_wrapper(chunkid):
            nonlocal chunks_received
            nonlocal chunks_failed
            result = await fetch_single_chunk_via_rpc(chunkid)
            if result is None:
                chunks_failed += 1
            else:
                chunks_received += 1

        get_and_proccess_new_activation_tickets()
        index_new_chunks()
        total_chunk_count = Chunk.select().where(Chunk.confirmed == True and Chunk.indexed == True).count()
        idx = 1
        for c in Chunk.select().where(Chunk.confirmed == True):
            print('Fetching {} chunk of {}'.format(idx, total_chunk_count))
            asyncio.run(fetch_chunk_wrapper(c.chunk_id))
            idx += 1
        self.assertEqual(chunks_received, CHUNK_NUMBER)
        self.assertEqual(chunks_failed, 0)

    def test_print_number_of_configrmed_chunks_in_mn_db(self):
        mns = Masternode.get_active_nodes()
        for mn in mns:
            client = mn.get_rpc_client()
            result = client.send_rpc_execute_sql('select count(id) from chunk where confirmed=true;')
            result_stored = client.send_rpc_execute_sql('select count(id) from chunk where stored=true;')
            chunk_count = result[0]['count(id)']
            stored_count = result_stored[0]['count(id)']
            print('{} has {} confirmed, {} stored chunks'.format(client.server_ip, chunk_count, stored_count))

    def test_download_regticket_humbnail_by_hash_from_all_mns(self):
        async def try_dl_thumbnail(client, hash):
            print(client.server_ip)
            try:
                result = await client.rpc_download_thumbnail(hash)
            except Exception as e:
                print(e)
                return

            if result is not None:
                print('Result is not None, has {} bytes'.format(len(result)))

            else:
                print('result is empty')

        # get regticket
        result = get_blockchain_connection().list_tickets("act")
        act_ticket_txids = list(filter(lambda x: len(x) == TXID_LENGTH, result))
        get_and_proccess_new_activation_tickets()
        index_new_chunks()
        mns = Masternode.get_active_nodes()

        for txid in act_ticket_txids:
            # get ticket by txid
            ticket = json.loads(get_blockchain_connection().get_ticket(txid))
            regticket_base64 = ticket['ticket']['art_ticket']

            regticket = RegistrationTicket(serialized_base64=regticket_base64)

            for mn in mns:
                client = mn.get_rpc_client()
                asyncio.run(try_dl_thumbnail(client, regticket.thumbnailhash))

            # print(regticket.thumbnailhash)

            # first - make sure thumbnailhash exists in our chunks DB
            # print(Chunk.select().where(Chunk.image_hash == regticket.thumbnailhash).count())

    def test_get_missing_chunk_ids(self):
        masternodes = list(Masternode.get_active_nodes())
        for mn in masternodes:
            client = mn.get_rpc_client()
            # sql = "select id from masternode where pastel_id='{}';".format(mn.pastel_id)
            # print(sql)

            # print(result[0]['id'])
            sql = '''select c.chunk_id from chunkmnranked r, chunk c where r.masternode_id in 
            (select id from masternode where pastel_id='{}') and c.stored=false'''.format(mn.pastel_id)
            result = client.send_rpc_execute_sql(sql)
            print(result)

    def test_chunk_fetcher_task_body(self):
        storage_index = list(get_chunkmanager().index_storage())
        self.assertEqual(len(storage_index), 0)

        self.assertEqual(Chunk.select().where(Chunk.stored == True).count(), 0)
        get_and_proccess_new_activation_tickets()
        refresh_masternode_list()
        index_new_chunks()
        asyncio.run(chunk_fetcher_task_body(pastel_id=REAL_MN_PASTEL_ID))
        # check that DB flags are 'stored' TODO: fix
        self.assertEqual(Chunk.select().where(Chunk.stored == True).count(), CHUNK_NUMBER)
        # check that we have this chunks
        for chunk in Chunk.select():
            data = get_chunkmanager().get_chunk_data(int(chunk.chunk_id))
            self.assertIsNotNone(data)
        storage_index = list(get_chunkmanager().index_storage())
        self.assertEqual(len(storage_index), CHUNK_NUMBER)
