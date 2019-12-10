import unittest
from unittest.mock import patch, Mock
from core_modules.database import MASTERNODE_DB, DB_MODELS, Masternode, Chunk, ChunkMnDistance, ChunkMnRanked, \
    ActivationTicket
from pynode.tasks import index_new_chunks, recalculate_mn_chunk_ranking_table, get_missing_chunk_ids, \
    refresh_masternode_list, update_masternode_list, move_confirmed_chunks_to_persistant_storage, \
    get_and_proccess_new_activation_tickets
from tests.ticket_data.actticket import ACTTICKET_DATA


class TestXORDistanceTask(unittest.TestCase):
    def setUp(self):
        MASTERNODE_DB.init(':memory:')
        MASTERNODE_DB.connect(reuse_if_open=True)
        MASTERNODE_DB.create_tables(DB_MODELS)
        Masternode.create(
            ext_address='127.0.0.1:444',
            pastel_id='jXZVtBmehoxYPotVrLdByFNNcB8jsryXhFPgqRa95i2x1mknbzSef1oGjnzfiwRtzReimfugvg41VtA7qGfDZR')
        Masternode.create(
            ext_address='127.0.0.1:4441',
            pastel_id='jXZVtBmehoxYPotVrLdByFNNcB7jsryXhFPgqRa95i2x1mknbzSef1oGjnzfiwRtzReimfugvg41VtA7qGfDZR')

    def test_xor_distance_task_with_2_chunks(self):
        Chunk.create(chunk_id='4529959709239007853998547086821683042815765622154307906125136018'
                              '25293195444578222995977844421809007120124095843869086665678514889'
                              '572116942841928123088049', image_hash=b'123123123')
        Chunk.create(chunk_id='4529959709239007853998547086821683042815765622154307906125136018'
                              '25293195444578222995977844421809007120124095843869086665678514889'
                              '572116942841928123088041', image_hash=b'123123123')
        self.assertEqual(Chunk.select()[0].indexed, False)
        index_new_chunks()
        self.assertEqual(len(ChunkMnDistance.select()), 4)
        self.assertEqual(Chunk.select()[0].indexed, True)
        self.assertEqual(Chunk.select()[1].indexed, True)

    def test_xor_distance_task_without_chunks(self):
        self.assertEqual(len(Chunk.select()), 0)
        index_new_chunks()
        self.assertEqual(len(ChunkMnDistance.select()), 0)

    def test_xor_distance_task_without_chunks_without_masternodes(self):
        Masternode.delete()
        self.assertEqual(len(Chunk.select()), 0)
        index_new_chunks()
        self.assertEqual(len(ChunkMnDistance.select()), 0)


class TestCalculateRankingTableTask(unittest.TestCase):
    def setUp(self):
        MASTERNODE_DB.init(':memory:')
        MASTERNODE_DB.connect(reuse_if_open=True)
        MASTERNODE_DB.create_tables(DB_MODELS)
        for i in range(3):
            Masternode.create(
                ext_address='127.0.0.1:444{}'.format(i),
                pastel_id='jXZVtBmehoxYPotVrLdByFNNcB8jsryXhFPgqRa95i2x1mknbzSef1oGjnzfiwRtzReimfugvg41VtA7qGfDZ{}'.format(
                    i))
            Chunk.create(chunk_id='1231231231231231232323934384834890089238429382938429384934{}'.format(i),
                         image_hash=b'asdasdasd')
        index_new_chunks()

    def test_calculate_ranks(self):
        self.assertEqual(ChunkMnRanked.select().count(), 0)
        recalculate_mn_chunk_ranking_table()
        self.assertEqual(ChunkMnRanked.select().count(), 9)

    def test_get_missing_chunks(self):
        pastel_id = 'jXZVtBmehoxYPotVrLdByFNNcB8jsryXhFPgqRa95i2x1mknbzSef1oGjnzfiwRtzReimfugvg41VtA7qGfDZ0'
        recalculate_mn_chunk_ranking_table()
        chunks = get_missing_chunk_ids(pastel_id)
        self.assertEqual(len(chunks), 3)

    def test_get_missing_chunks_2(self):
        pastel_id = 'jXZVtBmehoxYPotVrLdByFNNcB8jsryXhFPgqRa95i2x1mknbzSef1oGjnzfiwRtzReimfugvg41VtA7qGfDZ0'
        Chunk.update(stored=True).where(Chunk.id == 1).execute()
        recalculate_mn_chunk_ranking_table()
        chunks = get_missing_chunk_ids(pastel_id)
        self.assertEqual(len(chunks), 2)

mn_list = {
            'mn4': {
                'extKey': 'jXZVtBmehoxYPotVrLdByFNNcB8jsryXhFPgqRa95i2x1mknbzSef1oGjnzfiwRtzReimfugvg41VtA7qGfDZR',
                'extAddress': '18.216.28.255:4444'
            },
            'mn5': {
                'extKey': 'jXY39ehN4BWWpXLt4Q2zpcmypSAN9saWCweGRtJTxK87ktftjigfJwE6X9JoVfBduDjzEG4uBVR8Es6jVFMAbW',
                'extAddress': '18.191.111.96:4444'
            },
            'mn6': {
                'extKey': 'jXa2jiukvPktEdPvGo5nCLaMHxFRLneXMUNLGU4AUkuMmFq6ADerSJZg3Htd7rGjZo6HM92CgUFW1LjEwrKubd',
                'extAddress': '18.222.118.140:4444'
            }
        }


class RefreshMNListTestCase(unittest.TestCase):
    def setUp(self):
        MASTERNODE_DB.init(':memory:')
        MASTERNODE_DB.connect(reuse_if_open=True)
        MASTERNODE_DB.create_tables(DB_MODELS)

    @patch('cnode_connection.BlockChain', autospec=True)
    def test_refresh_masternode_list(self, bc_obj):
        bc_obj.return_value.masternode_list.return_value = mn_list
        self.assertEqual(Masternode.select().count(), 0)
        refresh_masternode_list()
        self.assertEqual(Masternode.select().count(), 3)
        self.assertEqual(ChunkMnDistance.select().count(), 0)

    @patch('cnode_connection.BlockChain', autospec=True)
    def test_calculate_xor_distances_for_masternodes(self, bc_obj):
        bc_obj.return_value.masternode_list.return_value = mn_list
        for i in range(3):
            Chunk.create(chunk_id='1231231231231231232323934384834890089238429382938429384934{}'.format(i),
                         image_hash=b'asdasdasd')
        refresh_masternode_list()
        self.assertEqual(Masternode.select().count(), 3)
        self.assertEqual(ChunkMnDistance.select().count(), 9)


class TmpStorageTaskTestCase(unittest.TestCase):
    @patch('core_modules.chunkmanager._chunkmanager', autospec=True)
    def test_tmp_storage_task(self, chunkmanager):
        chunkmanager.return_value.index_temp_storage.return_value = []
        move_confirmed_chunks_to_persistant_storage()
        chunkmanager.index_temp_storage.assert_called()


class ProcessNewActTicketsTaskTestCase(unittest.TestCase):
    def setUp(self):
        MASTERNODE_DB.init(':memory:')
        MASTERNODE_DB.connect(reuse_if_open=True)
        MASTERNODE_DB.create_tables(DB_MODELS)

    @patch('pynode.tasks.get_blockchain_connection', autospec=True)
    def test_task(self, get_blockchain_connection):
        get_blockchain_connection().list_tickets.return_value = ['asdasd']
        get_blockchain_connection().get_ticket.return_value = ACTTICKET_DATA
        self.assertEqual(Chunk.select().count(), 0)
        self.assertEqual(ActivationTicket.select().count(), 0)
        get_and_proccess_new_activation_tickets()
        self.assertEqual(ActivationTicket.select().count(), 1)
        self.assertEqual(Chunk.select().count(), 3)

    @patch('pynode.tasks.get_blockchain_connection', autospec=True)
    def test_process_twice(self, get_blockchain_connection):
        get_blockchain_connection().list_tickets.return_value = ['asdasd']
        get_blockchain_connection().get_ticket.return_value = ACTTICKET_DATA
        get_and_proccess_new_activation_tickets()
        get_and_proccess_new_activation_tickets()
        self.assertEqual(ActivationTicket.select().count(), 1)
        self.assertEqual(Chunk.select().count(), 3)

    @patch('pynode.tasks.get_blockchain_connection', autospec=True)
    def test_no_act_ticket(self, get_blockchain_connection):
        get_blockchain_connection().list_tickets.return_value = []
        get_and_proccess_new_activation_tickets()
        self.assertEqual(ActivationTicket.select().count(), 0)
        self.assertEqual(Chunk.select().count(), 0)


class GetMissingChunkTestCase(unittest.TestCase):
    def setUp(self):
        MASTERNODE_DB.init(':memory:')
        MASTERNODE_DB.connect(reuse_if_open=True)
        MASTERNODE_DB.create_tables(DB_MODELS)

    @patch('cnode_connection._blockchain')
    def test_get_missin_chunk_empty_db(self, bc):
        bc.pastelid = 'Somerandompastelid'
        get_missing_chunk_ids()
