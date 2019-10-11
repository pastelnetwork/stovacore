# -*- coding: utf-8 -*-

import unittest

from core_modules.model_validators import NetWorkSettings
from core_modules.model_validators import FingerprintField, LubyChunkField, LubyChunkHashField, LubySeedField, \
    ImageField, ThumbnailField, BytesField, StringField, StringChoiceField, IntegerField, SHA2256Field, SHA3512Field, \
    TXIDField, SignatureField, PubkeyField, BlockChainAddressField, UnixTimeField, NotImplementedType, \
    NotImplementedValidator


class TestFingerprintField(unittest.TestCase):
    def setUp(self):
        self.v = FingerprintField()

    def test_containertype(self):
        with self.assertRaises(TypeError):
            self.v.validate({})

    def test_length_min(self):
        with self.assertRaises(ValueError):
            data = [0.0 for _ in range(NetWorkSettings.DUPE_DETECTION_FINGERPRINT_SIZE - 1)]
            self.v.validate(data)

    def test_length_max(self):
        with self.assertRaises(ValueError):
            data = [0.0 for _ in range(NetWorkSettings.DUPE_DETECTION_FINGERPRINT_SIZE + 1)]
            self.v.validate(data)

    def test_innertype(self):
        with self.assertRaises(TypeError):
            data = [0 for _ in range(NetWorkSettings.DUPE_DETECTION_FINGERPRINT_SIZE)]
            self.v.validate(data)

    def test_innermin(self):
        with self.assertRaises(ValueError):
            data = [-1000000.0 for _ in range(NetWorkSettings.DUPE_DETECTION_FINGERPRINT_SIZE)]
            self.v.validate(data)

    def test_innermax(self):
        with self.assertRaises(ValueError):
            data = [1000000.0 for _ in range(NetWorkSettings.DUPE_DETECTION_FINGERPRINT_SIZE)]
            self.v.validate(data)

    def test_valid(self):
        data = [133.7 for _ in range(NetWorkSettings.DUPE_DETECTION_FINGERPRINT_SIZE)]
        self.v.validate(data)


class TestLubyChunkField(unittest.TestCase):
    def setUp(self):
        self.v = LubyChunkField()

    def test_containertype(self):
        with self.assertRaises(TypeError):
            self.v.validate({})

    def test_len_min(self):
        with self.assertRaises(ValueError):
            data = []
            self.v.validate(data)

    def test_len_max(self):
        with self.assertRaises(ValueError):
            data = [1234 for _ in range(NetWorkSettings.MAX_LUBY_CHUNKS + 1)]
            self.v.validate(data)

    def test_innertype(self):
        with self.assertRaises(TypeError):
            data = ["test" for _ in range(213)]
            self.v.validate(data)

    def test_innermin(self):
        with self.assertRaises(ValueError):
            data = [b'']
            self.v.validate(data)

    def test_innermax(self):
        with self.assertRaises(ValueError):
            data = [b'X' * (NetWorkSettings.CHUNKSIZE + 1)]
            self.v.validate(data)

    def test_valid(self):
        data = [b'X' * 64 for _ in range(100)]
        self.v.validate(data)


class TestLubyChunkHashField(unittest.TestCase):
    def setUp(self):
        self.v = LubyChunkHashField()

    def test_containertype(self):
        with self.assertRaises(TypeError):
            self.v.validate({})

    def test_len_min(self):
        with self.assertRaises(ValueError):
            data = []
            self.v.validate(data)

    def test_len_max(self):
        with self.assertRaises(ValueError):
            data = [1234 for _ in range(NetWorkSettings.MAX_LUBY_CHUNKS + 1)]
            self.v.validate(data)

    def test_innertype(self):
        with self.assertRaises(TypeError):
            data = ["test" for _ in range(2)]
            self.v.validate(data)

    def test_innersize_min(self):
        with self.assertRaises(ValueError):
            data = [b'X' * 63 for _ in range(4)]
            self.v.validate(data)

    def test_innersize_max(self):
        with self.assertRaises(ValueError):
            data = [b'X' * 65 for _ in range(5)]
            self.v.validate(data)

    def test_valid(self):
        data = [b'X' * 64 for _ in range(100)]
        self.v.validate(data)


class TestLubySeedField(unittest.TestCase):
    def setUp(self):
        self.v = LubySeedField()

    def test_containertype(self):
        with self.assertRaises(TypeError):
            self.v.validate({})

    def test_len_min(self):
        with self.assertRaises(ValueError):
            data = []
            self.v.validate(data)

    def test_len_max(self):
        with self.assertRaises(ValueError):
            data = [1234 for _ in range(NetWorkSettings.MAX_LUBY_CHUNKS + 1)]
            self.v.validate(data)

    def test_innertype(self):
        with self.assertRaises(TypeError):
            data = ["test" for _ in range(213)]
            self.v.validate(data)

    def test_innersize_min(self):
        with self.assertRaises(ValueError):
            data = [-1 for _ in range(4)]
            self.v.validate(data)

    def test_innersize_max(self):
        with self.assertRaises(ValueError):
            data = [2 ** 32 for _ in range(5)]
            self.v.validate(data)

    def test_valid(self):
        data = [x for x in range(1000)]
        self.v.validate(data)


class TestNotImplementedType(unittest.TestCase):
    def setUp(self):
        self.v = NotImplementedType()

    def test_notimplemented(self):
        with self.assertRaises(NotImplementedError):
            if self.v == "X":
                pass


class TestNotImplementedValidator(unittest.TestCase):
    def setUp(self):
        self.v = NotImplementedValidator()

    def test_notimplemented(self):
        with self.assertRaises(NotImplementedError):
            self.v.validate("something")


class TestImageField(unittest.TestCase):
    def setUp(self):
        self.v = ImageField()

    def test_type(self):
        with self.assertRaises(TypeError):
            self.v.validate(True)

    def test_min(self):
        data = b''
        with self.assertRaises(ValueError):
            self.v.validate(data)

    def test_max(self):
        data = b'A' * (NetWorkSettings.IMAGE_MAX_SIZE + 1)
        with self.assertRaises(ValueError):
            self.v.validate(data)

    def test_invalid_image(self):
        data = b'B' * NetWorkSettings.IMAGE_MAX_SIZE
        with self.assertRaises(OSError):
            self.v.validate(data)

    def test_valid(self):
        # 1x1px png
        data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x01\x03\x00\x00\x00%\xdbV' \
               b'\xca\x00\x00\x00\x03PLTE\xffM\x00\\58\x7f\x00\x00\x00\x01tRNS\xcc\xd24V\xfd\x00\x00\x00\nIDATx' \
               b'\x9ccb\x00\x00\x00\x06\x00\x0367|\xa8\x00\x00\x00\x00IEND\xaeB`\x82'
        self.v.validate(data)


class TestThumbnailField(unittest.TestCase):
    def setUp(self):
        self.v = ThumbnailField()

    def test_type(self):
        with self.assertRaises(TypeError):
            self.v.validate("2364326")

    def test_min(self):
        data = b''
        with self.assertRaises(ValueError):
            self.v.validate(data)

    def test_max(self):
        data = b'A' * (NetWorkSettings.THUMBNAIL_MAX_SIZE + 1)
        with self.assertRaises(ValueError):
            self.v.validate(data)

    def test_invalid_image(self):
        data = b'D' * NetWorkSettings.THUMBNAIL_MAX_SIZE
        with self.assertRaises(OSError):
            self.v.validate(data)

    def test_valid(self):
        # 1x1px png
        data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x01\x03\x00\x00\x00%\xdbV' \
               b'\xca\x00\x00\x00\x03PLTE\xffM\x00\\58\x7f\x00\x00\x00\x01tRNS\xcc\xd24V\xfd\x00\x00\x00\nIDATx' \
               b'\x9ccb\x00\x00\x00\x06\x00\x0367|\xa8\x00\x00\x00\x00IEND\xaeB`\x82'
        self.v.validate(data)


class TestIntegerField(unittest.TestCase):
    def setUp(self):
        self.v = IntegerField(minsize=10, maxsize=20)

    def test_type(self):
        with self.assertRaises(TypeError):
            self.v.validate("0")

    def test_min(self):
        with self.assertRaises(ValueError):
            self.v.validate(9)

    def test_max(self):
        with self.assertRaises(ValueError):
            self.v.validate(21)

    def test_valid(self):
        self.v.validate(10)
        self.v.validate(20)


class TestBytesField(unittest.TestCase):
    def setUp(self):
        self.v = BytesField(minsize=2, maxsize=5)

    def test_type(self):
        with self.assertRaises(TypeError):
            self.v.validate(0)

    def test_min(self):
        with self.assertRaises(ValueError):
            self.v.validate(b'X' * 1)

    def test_max(self):
        with self.assertRaises(ValueError):
            self.v.validate(b'X' * 6)

    def test_valid(self):
        self.v.validate(b'A' * 2)
        self.v.validate(b'B' * 5)


class TestStringField(unittest.TestCase):
    def setUp(self):
        self.v = StringField(minsize=5, maxsize=10)

    def test_type(self):
        with self.assertRaises(TypeError):
            self.v.validate(0)

    def test_min(self):
        with self.assertRaises(ValueError):
            self.v.validate("W" * 1)

    def test_max(self):
        with self.assertRaises(ValueError):
            self.v.validate("Z" * 12)

    # "ő" is a 2 byte utf character
    # >>> "ő".encode("utf-8")
    # b'\xc5\x91'
    def test_multibyte_size_min(self):
        with self.assertRaises(ValueError):
            self.v.validate("ő" * 2)

    def test_multibyte_size_max(self):
        with self.assertRaises(ValueError):
            self.v.validate("Z" * 9 + "ő")

    def test_valid(self):
        self.v.validate("Y" * 5)
        self.v.validate("X" * 10)
        self.v.validate("R" + "ő" * 2)
        self.v.validate("R" * 8 + "ő")


class TestStringChoiceField(unittest.TestCase):
    def setUp(self):
        self.v = StringChoiceField(choices=["foo", "bar"])

    def test_invalid_type(self):
        with self.assertRaises(TypeError):
            self.v.validate(123)

    def test_invalid_choice(self):
        with self.assertRaises(ValueError):
            self.v.validate("foobar")

    def test_valid(self):
        self.v.validate("foo")
        self.v.validate("bar")


class TestSHA2256Field(unittest.TestCase):
    def setUp(self):
        self.v = SHA2256Field()

    def test_invalid_type(self):
        with self.assertRaises(TypeError):
            self.v.validate(123)

    def test_invalid_min(self):
        with self.assertRaises(ValueError):
            self.v.validate(b'X' * 31)

    def test_invalid_max(self):
        with self.assertRaises(ValueError):
            self.v.validate(b'X' * 33)

    def test_valid(self):
        self.v.validate(b'X' * 32)


class TestSHA3512Field(unittest.TestCase):
    def setUp(self):
        self.v = SHA3512Field()

    def test_invalid_type(self):
        with self.assertRaises(TypeError):
            self.v.validate(123)

    def test_invalid_min(self):
        with self.assertRaises(ValueError):
            self.v.validate(b'X' * 63)

    def test_invalid_max(self):
        with self.assertRaises(ValueError):
            self.v.validate(b'X' * 65)

    def test_valid(self):
        self.v.validate(b'X' * 64)


class TestTXIDField(unittest.TestCase):
    def setUp(self):
        self.v = TXIDField()

    def test_invalid_type(self):
        with self.assertRaises(TypeError):
            self.v.validate(123)

    def test_invalid_min(self):
        with self.assertRaises(ValueError):
            self.v.validate('U' * 63)

    def test_invalid_max(self):
        with self.assertRaises(ValueError):
            self.v.validate('Y' * 65)

    def test_valid(self):
        self.v.validate('T' * 64)


class TestSignatureField(unittest.TestCase):
    def setUp(self):
        self.v = SignatureField()

    def test_type(self):
        with self.assertRaises(TypeError):
            self.v.validate(b"asd")

    def test_min(self):
        with self.assertRaises(ValueError):
            self.v.validate('B' * 153)

    def test_max(self):
        with self.assertRaises(ValueError):
            self.v.validate('Z' * 151)

    def test_valid(self):
        self.v.validate('X' * 152)


class TestPubkeyField(unittest.TestCase):
    def setUp(self):
        self.v = PubkeyField()

    def test_type(self):
        with self.assertRaises(TypeError):
            self.v.validate('test')

    def test_min(self):
        with self.assertRaises(ValueError):
            self.v.validate(b'W' * 65)

    def test_max(self):
        with self.assertRaises(ValueError):
            self.v.validate(b'Z' * 67)

    def test_valid(self):
        self.v.validate(b'Y' * 66)


class TestBlockChainAddressField(unittest.TestCase):
    def setUp(self):
        self.v = BlockChainAddressField()

    def test_type(self):
        with self.assertRaises(TypeError):
            self.v.validate(b'test')

    def test_min(self):
        with self.assertRaises(ValueError):
            self.v.validate("W" * 25)

    def test_max(self):
        with self.assertRaises(ValueError):
            self.v.validate("Z" * 36)

    def test_valid(self):
        self.v.validate("Y" * 30)


class TestUnixTimeField(unittest.TestCase):
    def setUp(self):
        self.v = UnixTimeField()

    def test_type(self):
        with self.assertRaises(TypeError):
            self.v.validate("test")

    def test_min(self):
        with self.assertRaises(ValueError):
            self.v.validate(-1)

    def test_max(self):
        with self.assertRaises(ValueError):
            self.v.validate(2 ** 32)

    def test_valid(self):
        self.v.validate(1538056615)
