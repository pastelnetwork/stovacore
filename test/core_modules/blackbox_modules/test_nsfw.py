import unittest

from core_modules.blackbox_modules.nsfw import NSFWDetector


class TestNSFW(unittest.TestCase):
    def setUp(self):
        # 1x1px png with color FF4D00 and opacity 0.8
        self.image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x01\x03\x00\x00\x00' \
                          b'%\xdbV\xca\x00\x00\x00\x06PLTE\xffM\x00\x01\x01\x01\x8e\x1e\xe5\x1b\x00\x00\x00\x01tRNS' \
                          b'\xcc\xd24V\xfd\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00' \
                          b'IEND\xaeB`\x82'

    def test_nsfw_get_score(self):
        score = NSFWDetector.get_score(self.image_data)
        self.assertEqual(score, 0.8916751220822334)

    def test_nsfw_is_nsfw(self):
        is_nsfw = NSFWDetector.is_nsfw(self.image_data)
        self.assertFalse(is_nsfw)
