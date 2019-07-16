from peewee import Model, SqliteDatabase, BlobField, DateTimeField

from core_modules.settings import NetWorkSettings

db = SqliteDatabase(NetWorkSettings.MN_DATABASE_FILE)


class UploadCode(Model):
    upload_code = BlobField()
    regticket = BlobField()
    created = DateTimeField()

    class Meta:
        database = db
        table_name = 'upload_code'
