from peewee import Model, SqliteDatabase, DateTimeField, FloatField, IntegerField, ForeignKeyField, CharField

db = SqliteDatabase(None)

REGTICKET_STATUS_CREATED = 0


class RegticketDB(Model):
    worker_fee = FloatField(null=True)
    status = IntegerField(default=REGTICKET_STATUS_CREATED)
    created = DateTimeField()
    blocknum = IntegerField()

    class Meta:
        database = db
        table_name = 'regticket'
