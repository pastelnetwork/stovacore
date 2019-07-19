from peewee import Model, SqliteDatabase, DateTimeField, FloatField, IntegerField, ForeignKeyField, CharField

db = SqliteDatabase(None)

REGTICKET_STATUS_CREATED = 0


class MasternodeDB(Model):
    py_address = CharField()
    payee = CharField()
    py_pub_key = CharField()

    class Meta:
        database = db
        table_name = 'masternode'


class RegticketDB(Model):
    worker_fee = FloatField(null=True)
    status = IntegerField(default=REGTICKET_STATUS_CREATED)
    created = DateTimeField()
    mn0 = ForeignKeyField(MasternodeDB)
    mn1 = ForeignKeyField(MasternodeDB)
    mn2 = ForeignKeyField(MasternodeDB)

    class Meta:
        database = db
        table_name = 'regticket'
