import os

from peewee import Model, SqliteDatabase, DateTimeField, FloatField, IntegerField, BlobField, CharField, BooleanField

from core_modules.helpers import get_pynode_digest_hex
from core_modules.rpc_client import RPCClient
from wallet.settings import get_thumbnail_dir

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


class Artwork(Model):
    act_ticket_txid = CharField(unique=True)
    artist_pastelid = CharField()
    artwork_title = CharField()
    total_copies = IntegerField()
    artist_name = CharField()
    artist_website = CharField()
    artist_written_statement = CharField()
    artwork_series_name = CharField()
    artwork_creation_video_youtube_url = CharField()
    artwork_keyword_set = CharField()
    imagedata_hash = BlobField()
    blocknum = IntegerField()  # use negative blocknum to store invalid act ticket txids
    order_block_txid = CharField()

    class Meta:
        database = db
        table_name = 'artwork'

    def get_thumbnail_path(self):
        thumbnail_filename = '{}.png'.format(self.act_ticket_txid)
        return os.path.join(get_thumbnail_dir(), thumbnail_filename)

    def get_image_hash_digest(self):
        return get_pynode_digest_hex(self.imagedata_hash)


WALLET_DB_MODELS = [RegticketDB, Masternode, Artwork]
