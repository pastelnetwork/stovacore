from peewee import Model, SqliteDatabase, DateTimeField, FloatField, IntegerField, BlobField, CharField

db = SqliteDatabase(None)

REGTICKET_STATUS_CREATED = 0


class RegticketDB(Model):
    worker_fee = FloatField(null=True)
    status = IntegerField(default=REGTICKET_STATUS_CREATED)
    created = DateTimeField()
    blocknum = IntegerField()
    serialized_regticket = BlobField()
    path_to_image = CharField(null=True)

    class Meta:
        database = db
        table_name = 'regticket'
