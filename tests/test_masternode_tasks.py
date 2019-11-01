import unittest

from core_modules.database import MASTERNODE_DB, DB_MODELS, Masternode, Chunk, ChunkMnDistance, ChunkMnRanked
from pynode.masternode_logic import index_new_chunks, recalculate_mn_chunk_ranking_table


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

    # TODO: test actual ranking
