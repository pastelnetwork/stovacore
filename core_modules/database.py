from peewee import Model, SqliteDatabase, BlobField, DateTimeField

from core_modules.settings import NetWorkSettings

db = SqliteDatabase(NetWorkSettings.MN_DATABASE_FILE)


class UploadCode(Model):
    public_key = BlobField()
    upload_code = BlobField()
    created = DateTimeField()

    class Meta:
        database = db
        table_name = 'upload_code'
