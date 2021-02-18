"""
Low-level fields implementation for ticket models.
"""

import io

from PIL import Image

from .settings import Settings


class FieldValidator:
    pass


class NotImplementedType(FieldValidator):
    def __eq__(self, other):
        raise NotImplementedError()


class NotImplementedValidator(FieldValidator):
    def validate(self, other):
        raise NotImplementedError()


class LengthValidator(FieldValidator):
    accepted_type = NotImplementedType()

    def __init__(self, minsize, maxsize):
        self.minsize = minsize
        self.maxsize = maxsize

    def validate(self, value):
        if type(value) != self.accepted_type:
            raise TypeError("%s: value is not %s, was: %s" % (self, self.accepted_type, type(value)))

        if len(value) < self.minsize or len(value) > self.maxsize:
            raise ValueError("%s: Length is out of bound (value < %s or value > %s), was: %s" % (self,
                                                                                                 self.minsize,
                                                                                                 self.maxsize,
                                                                                                 len(value)))

        return value


class NumberValidator(FieldValidator):
    accepted_type = NotImplementedType()

    def __init__(self, minsize, maxsize):
        self.minsize = minsize
        self.maxsize = maxsize

    def validate(self, value):
        if type(value) != self.accepted_type:
            raise TypeError("%s: value is not %s, was: %s" % (self, self.accepted_type, type(value)))

        if value < self.minsize or value > self.maxsize:
            raise ValueError("%s: Value is out of bound (value < %s or value > %s), was: %s" % (self,
                                                                                                self.minsize,
                                                                                                self.maxsize,
                                                                                                value))

        return value


class StringField(FieldValidator):
    def __init__(self, minsize, maxsize):
        self.minsize = minsize
        self.maxsize = maxsize

    def validate(self, value):
        if type(value) != str:
            raise TypeError("%s: value is not str, was: %s" % (self, type(value)))

        encoded = value.encode("utf-8")
        if len(encoded) < self.minsize or len(encoded) > self.maxsize:
            raise ValueError("%s: encoded value is out of bounds (value < %s or value > %s), was: %s" % (self,
                                                                                                         self.minsize,
                                                                                                         self.maxsize,
                                                                                                         len(encoded)))

        return value


class StringChoiceField(FieldValidator):
    def __init__(self, choices):
        self.choices = set(choices)

    def validate(self, value):
        if type(value) != str:
            raise TypeError("%s: value is not list, was: %s" % (self, type(value)))

        if value not in self.choices:
            raise ValueError("%s: Value not in choices: %s" % (self, self.choices))

        return value


class IntegerField(NumberValidator):
    accepted_type = int


class FloatField(NumberValidator):
    accepted_type = float


class ContainerWithElementValidator(LengthValidator):
    accepted_type = list
    element_validator = NotImplementedValidator()

    def validate(self, value):
        super().validate(value)

        for element in value:
            self.element_validator.validate(element)

        return value


class FingerprintField(ContainerWithElementValidator):
    container_type = list
    # TODO: make sure these are correct values
    element_validator = FloatField(minsize=-1000, maxsize=1000)

    def __init__(self):
        super().__init__(Settings.DUPE_DETECTION_FINGERPRINT_SIZE,
                         Settings.DUPE_DETECTION_FINGERPRINT_SIZE)


class ImageTypeValidatorField(LengthValidator):
    accepted_type = bytes

    def __init__(self, minsize, maxsize):
        super().__init__(minsize, maxsize)

    def validate(self, value):
        super().validate(value)

        # TODO: move this to a separate isolated process as image is user-supplied!
        imagefile = io.BytesIO(value)
        Image.open(imagefile)
        return value


class ImageField(ImageTypeValidatorField):
    def __init__(self):
        super().__init__(1, Settings.IMAGE_MAX_SIZE)


class ThumbnailField(ImageTypeValidatorField):
    def __init__(self):
        super().__init__(1, Settings.THUMBNAIL_MAX_SIZE)

    def __str__(self):
        return 'Thumbnail field'


class BytesField(LengthValidator):
    accepted_type = bytes


class SHA3512Field(BytesField):
    def __init__(self):
        super().__init__(minsize=64, maxsize=64)


class SHA2256Field(BytesField):
    def __init__(self):
        super().__init__(minsize=32, maxsize=32)


class TXIDField(StringField):
    def __init__(self):
        super().__init__(minsize=64, maxsize=64)


class UUIDField(StringField):
    def __init__(self):
        super().__init__(minsize=36, maxsize=36)


class SignatureField(StringField):
    def __init__(self):
        super().__init__(minsize=152, maxsize=152)


class PubkeyField(BytesField):
    def __init__(self):
        super().__init__(minsize=66, maxsize=66)


class PastelIDField(StringField):
    def __init__(self):
        super().__init__(minsize=86, maxsize=86)


class BlockChainAddressField(StringField):
    def __init__(self):
        super().__init__(minsize=26, maxsize=35)


class UnixTimeField(IntegerField):
    def __init__(self):
        super().__init__(minsize=0, maxsize=2**32-1)


class LubyChunkHashField(ContainerWithElementValidator):
    container_type = list
    element_validator = SHA3512Field()

    def __init__(self):
        super().__init__(1, Settings.MAX_LUBY_CHUNKS)


class LubySeedField(ContainerWithElementValidator):
    container_type = list
    element_validator = IntegerField(minsize=0, maxsize=2**32-1)

    def __init__(self):
        super().__init__(1, Settings.MAX_LUBY_CHUNKS)


class LubyChunkField(ContainerWithElementValidator):
    container_type = list
    element_validator = BytesField(minsize=1, maxsize=Settings.CHUNKSIZE)

    def __init__(self):
        super().__init__(1, Settings.MAX_LUBY_CHUNKS)
