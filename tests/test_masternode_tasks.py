import unittest

from core_modules.database import db, DB_MODELS, Masternode, Chunk, ChunkMnDistance
from masternode_prototype.masternode_logic import index_new_chunks


class TestXORDistanceTask(unittest.TestCase):
    def setUp(self):
        db.init(':memory:')
        db.connect(reuse_if_open=True)
        db.create_tables(DB_MODELS)
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
