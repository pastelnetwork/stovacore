import unittest
from core_modules.ticket_models import ImageData

from tests import png_1x1_data


class TestLuby(unittest.TestCase):
    def setUp(self):
        # self.data = b'A' * 1024 * 512 + b'A' * 100
        self.data = png_1x1_data

    def test_compare_luby_hashes_from_same_seed(self):
        id1 = ImageData(dictionary={"image": self.data,
                                    "lubychunks": ImageData.generate_luby_chunks(self.data),
                                    "thumbnail": ImageData.generate_thumbnail(self.data),
                                    })
        seeds = id1.get_luby_seeds()
        id2 = ImageData(dictionary={"image": self.data,
                                    "lubychunks": ImageData.generate_luby_chunks(self.data, seeds),
                                    "thumbnail": ImageData.generate_thumbnail(self.data)
                                    })
        self.assertEqual(id1.get_luby_hashes(), id2.get_luby_hashes())
