from peewee import Model, SqliteDatabase, BlobField, DateTimeField, DecimalField, BooleanField

from core_modules.settings import NetWorkSettings

db = SqliteDatabase(NetWorkSettings.MN_DATABASE_FILE)


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
    is_valid_mn1 = BooleanField(null=True)
    mn2_pk = BlobField(null=True)
    is_valid_mn2 = BooleanField(null=True)

    class Meta:
        database = db
        table_name = 'upload_code'
