import os
import stat
import random
import unittest
from unittest.mock import patch
import shutil
import tempfile
import warnings

from core_modules.chunk_storage import ChunkStorage
from core_modules.chunkmanager import get_chunkmanager
from core_modules.database import MASTERNODE_DB, DB_MODELS, Chunk
from core_modules.helpers import get_pynode_digest_int, bytes_to_chunkid
from core_modules.blackbox_modules import luby
from core_modules.masternode_ticketing import masternode_place_image_data_in_chunkstorage
from core_modules.ticket_models import RegistrationTicket, ImageData
from pynode.tasks import move_confirmed_chunks_to_persistant_storage
from tests.system_tests.test_system import switch_pastelid, CLIENT_PASTELID, PASSPHRASE
from tests.test_utils import png_1x1_data
from wallet.art_registration_client import ArtRegistrationClient


def get_regticket():
    image = ImageData(dictionary={
        "image": png_1x1_data,
        "lubychunks": ImageData.generate_luby_chunks(png_1x1_data),
        "thumbnail": ImageData.generate_thumbnail(png_1x1_data),
    })

    return RegistrationTicket(dictionary={
        "artist_name": '',
        "artist_website": '',
        "artist_written_statement": '',

        "artwork_title": '',
        "artwork_series_name": '',
        "artwork_creation_video_youtube_url": '',
        "artwork_keyword_set": '',
        "total_copies": 0,

        "fingerprints": image.generate_fingerprints(),
        "lubyhashes": image.get_luby_hashes(),
        "lubyseeds": image.get_luby_seeds(),
        "thumbnailhash": image.get_thumbnail_hash(),

        "author": 'jXZDyqqMDXSz1ycBLCZJ82U2GCSL7m8KTet3i685pFroMdjGaPvdCmVZWrkxoKn1H7wSHibVEohHV7u5juDrne',
        "order_block_txid": '77996c90fd99ee60788333da62f7586e2f7b1c61d399484c2379927cba8f1356',
        "blocknum": 500,
        "imagedata_hash": image.get_artwork_hash(),
    })


class TestChunkStorageInit(unittest.TestCase):
    def test_chunkstorage_creation_umask(self):
        test_dir = tempfile.mkdtemp()
        shutil.rmtree(test_dir)
        ChunkStorage(test_dir, mode=0o0700)
        dirstat = os.stat(test_dir)
        permissions = stat.filemode(dirstat.st_mode)
        self.assertEqual(permissions, "drwx------")


class TestChunkStorageInterface(unittest.TestCase):
    def setUp(self):
        CHUNK_SIZE = 1024 * 1024

        random.seed(236823823)
        self.chunk_data = random.getrandbits(CHUNK_SIZE * 8).to_bytes(CHUNK_SIZE, byteorder="big")
        self.chunk_digest = get_pynode_digest_int(self.chunk_data)

        self.test_dir = tempfile.mkdtemp()
        self.cs = ChunkStorage(self.test_dir, mode=0o0700)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_invalid_chunkname_type(self):
        with self.assertRaises(TypeError):
            self.cs.get("test")

    def test_short_chunkname(self):
        with self.assertRaises(FileNotFoundError):
            self.cs.get(1)

    def test_put_get(self):
        self.cs.put(self.chunk_digest, self.chunk_data)
        data = self.cs.get(self.chunk_digest)
        self.assertEqual(self.chunk_data, data)

    def test_get_offset(self):
        self.cs.put(self.chunk_digest, self.chunk_data)
        data = self.cs.get(self.chunk_digest, offset=1000, length=20)
        self.assertEqual(data, b'.na\x8e\x86\xf6\n\xf7)\xbbH\xf5p{\xe4g\x99\x8b\x88\r')

    def test_get_nosuchfile(self):
        with self.assertRaises(FileNotFoundError):
            self.cs.get(123456789)

    def test_delete(self):
        self.cs.put(self.chunk_digest, self.chunk_data)
        self.cs.delete(self.chunk_digest)
        with self.assertRaises(FileNotFoundError):
            self.cs.get(self.chunk_digest)

    def test_exists(self):
        self.cs.put(self.chunk_digest, self.chunk_data)
        self.assertTrue(self.cs.exists(self.chunk_digest))

    def test_exists_nosuchfile(self):
        self.assertFalse(self.cs.exists(213697237))

    def test_verify(self):
        self.cs.put(self.chunk_digest, self.chunk_data)
        self.assertTrue(self.cs.verify(self.chunk_digest))

    def test_verify_corrupted_file(self):
        self.cs.put(self.chunk_digest, b'random data')
        self.assertFalse(self.cs.verify(self.chunk_digest))

    def test_index(self):
        self.cs.put(self.chunk_digest, self.chunk_data)
        self.assertListEqual([self.chunk_digest], list(self.cs.index()))


class TestLuby(unittest.TestCase):
    def test_luby_decode_encoded(self):
        redundancy_factor = 2
        block_size = 1024

        data = b'A' * 1024 * 512 + b'A' * 100  # test for padding
        blocks = luby.encode(redundancy_factor, block_size, data)
        decoded = luby.decode(blocks)
        self.assertEqual(data, decoded)

    def test_luby_encode_2_times_compare_result(self):
        redundancy_factor = 3
        block_size = 1024

        data = b'A' * 1024 * 512 + b'A' * 100  # test for padding
        blocks1 = luby.encode(redundancy_factor, block_size, data)
        blocks2 = luby.encode(redundancy_factor, block_size, data)
        self.assertNotEqual(blocks1[0], blocks2[0])
        decoded1 = luby.decode(blocks1)
        decoded2 = luby.decode(blocks2)

        self.assertEqual(decoded1, decoded2)

    def test_reconstruct_with_same_seed(self):
        redundancy_factor = 3
        block_size = 1024

        data = b'A' * 1024 * 512 + b'A' * 100  # test for padding
        blocks1 = luby.encode(redundancy_factor, block_size, data)
        seeds = luby.get_seeds(blocks1)
        blocks2 = luby.encode(redundancy_factor, block_size, data, seeds)
        self.assertEqual(blocks1[0], blocks2[0])


class RegticketImageToChunkStorageTestCase(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter('ignore')
        MASTERNODE_DB.init(':memory:')
        MASTERNODE_DB.connect(reuse_if_open=True)
        MASTERNODE_DB.create_tables(DB_MODELS)

    @patch('core_modules.chunkmanager.ChunkStorage', autospec=True)
    def test_place_in_chunkstorage(self, chunkstorage):
        image_data = png_1x1_data
        regticket = get_regticket()
        masternode_place_image_data_in_chunkstorage(regticket, image_data)
        self.assertEqual(Chunk.select().count(), 2)


class ChunkFileNamesTestCase(unittest.TestCase):
    def setUp(self):
        # warnings.simplefilter('ignore')
        # MASTERNODE_DB.init(':memory:')
        # MASTERNODE_DB.connect(reuse_if_open=True)
        # MASTERNODE_DB.create_tables(DB_MODELS)
        switch_pastelid(CLIENT_PASTELID, PASSPHRASE)
        MASTERNODE_DB.init(':memory:')
        MASTERNODE_DB.connect(reuse_if_open=True)
        MASTERNODE_DB.create_tables(DB_MODELS)
        # cleanup chunk storage
        from cnode_connection import basedir
        import shutil
        try:
            shutil.rmtree(os.path.join(basedir, "chunkdata"))
            shutil.rmtree(os.path.join(basedir, "tmpstorage"))
        except FileNotFoundError:
            pass

    def tearDown(self) -> None:
        tmp_storage_path = get_chunkmanager().get_tmp_storage_path()
        shutil.rmtree(tmp_storage_path)
        storage_path = get_chunkmanager().get_storage_path()
        shutil.rmtree(storage_path)

    def test_chunk_id_to_filename(self):
        # create regticket
        regticket = ArtRegistrationClient.generate_regticket(
            png_1x1_data,
            {
                'artist_name': 'artist_name',
                'artist_website': 'artist_website',
                'artist_written_statement': 'artist_written_statement',
                'artwork_title': 'artwork_title',
                'artwork_series_name': 'artwork_series_name',
                'artwork_creation_video_youtube_url': 'artwork_creation_video_youtube_url',
                'artwork_keyword_set': 'artwork_keyword_set',
                'total_copies': 99, 'copy_price': 555
            })

        # emulate what we do on MN0 when storing data to chunkstorage
        imagedata = ImageData(dictionary={
            "image": png_1x1_data,
            "lubychunks": ImageData.generate_luby_chunks(png_1x1_data, seeds=regticket.lubyseeds),
            "thumbnail": ImageData.generate_thumbnail(png_1x1_data),
        })
        artwork_hash = imagedata.get_artwork_hash()
        self.assertEqual(artwork_hash, regticket.imagedata_hash)
        masternode_place_image_data_in_chunkstorage(regticket, png_1x1_data)
        chunkids = list(get_chunkmanager().index_temp_storage())

        # verify that our two chunks are actually in this chunksids list
        # get image chunks IDs from regticket
        image_chunkid = bytes_to_chunkid(regticket.lubyhashes[0])  # for very small image this is only 1 hash in list
        # get thumbnail chunk ID from regticket
        thumbnail_chunkid = bytes_to_chunkid(regticket.thumbnailhash)
        self.assertIn(image_chunkid, chunkids)
        self.assertIn(thumbnail_chunkid, chunkids)

        # good. now we've stored image and thumbnail in tmpstorage.
        # let's move it to regular storage
        self.assertEqual(Chunk.select().count(), 2)  # expect 2 chunks - image and thumbnail
        self.assertEqual(Chunk.select().where(Chunk.confirmed == False).count(),
                         2)  # expect 2 chunks - image and thumbnail
        # # set Chunk.confirmed  = True as if we've processed activation ticket
        Chunk.update(confirmed=True).execute()
        move_confirmed_chunks_to_persistant_storage()

        # try chunkstorage.get by chunk ID from regticket
        # in regticket list of lubyhashes are chunks IDs.
        image_chunk = get_chunkmanager().get_chunk_data(image_chunkid)
        thmbnail_chunk = get_chunkmanager().get_chunk_data(thumbnail_chunkid)
        self.assertIsNotNone(image_chunk)
        print(len(image_chunk))
        self.assertIsNotNone(thmbnail_chunk)
