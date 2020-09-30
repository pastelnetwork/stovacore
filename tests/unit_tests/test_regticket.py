import base64
import json
from unittest import TestCase
from tests.test_utils import png_1x1_data
from core_modules.ticket_models import RegistrationTicket, ImageData, Signature


def generate_test_regticket():
    image = ImageData(dictionary={
        "image": png_1x1_data,
        "lubychunks": ImageData.generate_luby_chunks(png_1x1_data),
        "thumbnail": ImageData.generate_thumbnail(png_1x1_data),
    })
    regticket = RegistrationTicket(dictionary={
        "artist_name": 'name',
        "artist_website": 'website',
        "artist_written_statement": 'some data',

        "artwork_title": 'title',
        "artwork_series_name": 'series',
        "artwork_creation_video_youtube_url": 'video.url',
        "artwork_keyword_set": 'key.word.set',
        "total_copies": 23,
        # "copy_price": copy_price,

        "fingerprints": image.generate_fingerprints(),
        "lubyhashes": image.get_luby_hashes(),
        "lubyseeds": image.get_luby_seeds(),
        "thumbnailhash": image.get_thumbnail_hash(),

        "author": ''.join('A' for x in range(86)),
        "order_block_txid": ''.join('A' for x in range(64)),
        "blocknum": 1,
        "imagedata_hash": image.get_artwork_hash(),
    })
    return regticket


class RegticketTestCase(TestCase):
    def setUp(self) -> None:
        pass

    def test_create_regticket(self):
        regticket = generate_test_regticket()
        serialized = regticket.serialize_base64()
        self.assertEqual(type(serialized), str)
        restored = RegistrationTicket(serialized_base64=serialized)
        self.assertEqual(restored.artist_name, regticket.artist_name)
        self.assertEqual(restored.fingerprints, regticket.fingerprints)
        self.assertEqual(restored.imagedata_hash, regticket.imagedata_hash)

    def test_prepare_cnode_artticket_data(self):
        regticket = generate_test_regticket()

        signatures_dict = {
            "artist": {'pastelid': 'signature'},
            "mn2": {'pastelid': 'signature'},
            "mn3": {'pastelid': 'signature'}
        }

        # write final ticket into blockchain
        art_ticket_data = {
            'cnode_package': regticket.get_cnode_package(),
            'signatures_dict': signatures_dict,
            'key1': 'somekey1',  # artist_signature.pastelid,
            'key2': 'somekey2',
            'art_block': 1,
            'fee': 100
        }
        self.assertEqual(type(art_ticket_data['cnode_package']), str)
        cnode_package_dict = json.loads(base64.b64decode(art_ticket_data['cnode_package']))
        self.assertEqual(cnode_package_dict['version'], 1)
        self.assertEqual(cnode_package_dict['author'], regticket.author)
        self.assertEqual(cnode_package_dict['blocknum'], regticket.blocknum)
        app_ticket = RegistrationTicket(serialized_base64=cnode_package_dict['app_ticket'])
        self.assertEqual(app_ticket.author, regticket.author)
        self.assertEqual(app_ticket.imagedata_hash, regticket.imagedata_hash)
