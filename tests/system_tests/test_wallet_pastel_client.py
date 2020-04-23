import asyncio
import os
import shutil
import unittest

from tests.system_tests.test_system import CLIENT_PASTELID, PASSPHRASE
from wallet.database import db, WALLET_DB_MODELS
from wallet.http_server import get_pastel_client
from wallet.settings import get_thumbnail_dir
from wallet.tasks import refresh_masternode_list


class PastelClientTestCase(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault('PASTEL_ID', CLIENT_PASTELID)
        os.environ.setdefault('PASSPHRASE', PASSPHRASE)
        os.environ.setdefault('APP_DIR', os.getcwd())
        db.init(':memory:')
        db.connect(reuse_if_open=True)
        db.create_tables(WALLET_DB_MODELS)
        if not os.path.exists(get_thumbnail_dir()):
            os.mkdir(get_thumbnail_dir())

    def tearDown(self) -> None:
        shutil.rmtree(get_thumbnail_dir())

    def test_get_artwork_data(self):
        async def get_artwork_data():
            artwork_data = await get_pastel_client().get_artworks_data()
            self.assertEqual(len(artwork_data), 3)
        refresh_masternode_list()
        asyncio.run(get_artwork_data())
        asyncio.run(get_artwork_data())  # check if 2nd run it does not fetch data from blockchain
