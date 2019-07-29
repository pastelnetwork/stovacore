from peewee import Model, SqliteDatabase, BlobField, DateTimeField, DecimalField

from core_modules.settings import NetWorkSettings

db = SqliteDatabase(NetWorkSettings.MN_DATABASE_FILE)


class UploadCode(Model):
    upload_code = BlobField(unique=True)
    regticket = BlobField()
    artists_signature_ticket = BlobField()
    created = DateTimeField()
    image_data = BlobField(null=True)
    localfee = DecimalField(null=True)

    class Meta:
        database = db
        table_name = 'upload_code'
