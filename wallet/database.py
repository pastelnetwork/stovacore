from peewee import Model, SqliteDatabase, DateTimeField, FloatField, IntegerField, BlobField, CharField, BooleanField

from core_modules.rpc_client import RPCClient

db = SqliteDatabase(None)

REGTICKET_STATUS_CREATED = 0


class RegticketDB(Model):
    worker_fee = FloatField(null=True)
    status = IntegerField(default=REGTICKET_STATUS_CREATED)
    created = DateTimeField()
    blocknum = IntegerField()
    serialized_regticket = BlobField()
    serialized_signature = BlobField()
    path_to_image = CharField(null=True)
    burn_tx_id = CharField(null=True)
    upload_code_mn0 = BlobField(null=True)
    upload_code_mn1 = BlobField(null=True)
    upload_code_mn2 = BlobField(null=True)
    image_hash = BlobField()

    class Meta:
        database = db
        table_name = 'regticket'


class Masternode(Model):
    ext_address = CharField(unique=True)  # ip:port
    pastel_id = CharField(unique=True)
    active = BooleanField(default=True)  # optionally disable masternode

    class Meta:
        database = db
        table_name = 'masternode'

    def get_rpc_client(self):
        ip, py_rpc_port = self.ext_address.split(':')
        rpc_client = RPCClient(self.pastel_id, ip, py_rpc_port)
        return rpc_client

    @classmethod
    def get_active_nodes(cls):
        return Masternode.select().where(Masternode.active == True)
