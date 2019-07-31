from peewee import Model, SqliteDatabase, BlobField, DateTimeField, DecimalField, BooleanField, IntegerField, CharField

from core_modules.settings import NetWorkSettings

db = SqliteDatabase(NetWorkSettings.MN_DATABASE_FILE)

REGTICKET_STATUS_CREATED = 0
REGTICKET_STATUS_ERROR = -1
REGTICKET_STATUS_PLACED_ON_BLOCKCHAIN = 1

REGTICKET_STATUS_CHOICES = ((REGTICKET_STATUS_CREATED, 'Created'),
                            (REGTICKET_STATUS_ERROR, 'Error'),
                            (REGTICKET_STATUS_PLACED_ON_BLOCKCHAIN, 'Placed on blockchain'),)

# TODO: rename to `Regticket`
class UploadCode(Model):
    upload_code = BlobField(unique=True)
    regticket = BlobField()
    artist_pk = BlobField()
    image_hash = BlobField()
    artists_signature_ticket = BlobField()
    created = DateTimeField()
    image_data = BlobField(null=True)
    localfee = DecimalField(null=True)
    is_valid_mn0 = BooleanField(null=True)
    mn1_pk = BlobField(null=True)
    mn1_serialized_signature = BlobField(null=True)
    is_valid_mn1 = BooleanField(null=True)
    mn2_pk = BlobField(null=True)
    mn2_serialized_signature = BlobField(null=True)
    is_valid_mn2 = BooleanField(null=True)
    status = IntegerField(choices=REGTICKET_STATUS_CHOICES, default=REGTICKET_STATUS_CREATED)
    error = CharField(null=True)

    class Meta:
        database = db
        table_name = 'upload_code'
