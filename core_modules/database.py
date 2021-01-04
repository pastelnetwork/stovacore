import json

from peewee import (Model, SqliteDatabase, BlobField, DateTimeField, DecimalField, BooleanField, IntegerField,
                    CharField,
                    ForeignKeyField)

from cnode_connection import get_blockchain_connection
from core_modules.helpers import bytes_to_chunkid
from core_modules.rpc_client import RPCClient
from core_modules.settings import Settings
from core_modules.ticket_models import RegistrationTicket, Signature

MASTERNODE_DB = SqliteDatabase(None)

REGTICKET_STATUS_CREATED = 0
REGTICKET_STATUS_ERROR = -1
REGTICKET_STATUS_PLACED_ON_BLOCKCHAIN = 1

REGTICKET_STATUS_CHOICES = ((REGTICKET_STATUS_CREATED, 'Created'),
                            (REGTICKET_STATUS_ERROR, 'Error'),
                            (REGTICKET_STATUS_PLACED_ON_BLOCKCHAIN, 'Placed on blockchain'),)


class Regticket(Model):
    upload_code = BlobField(unique=True, null=True)
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
    confirmed = BooleanField(default=False)  # track if confirmation ticket for a given regticket exists

    class Meta:
        database = MASTERNODE_DB
        table_name = 'regticket'

    def write_to_blockchain(self):
        ticket = RegistrationTicket(serialized=self.regticket)
        current_block = get_blockchain_connection().getblockcount()
        # verify if confirmation receive for 5 blocks or less from regticket creation.
        if current_block - ticket.blocknum > Settings.MAX_CONFIRMATION_DISTANCE_IN_BLOCKS:
            self.status = REGTICKET_STATUS_ERROR
            error_msg = 'Second confirmation received too late - current block {}, regticket block: {}'. \
                format(current_block, ticket.blocknum)
            self.error = error_msg
            raise Exception(error_msg)

        artist_signature = Signature(
            serialized=self.artists_signature_ticket)
        mn2_signature = Signature(
            serialized=self.mn1_serialized_signature)
        mn3_signature = Signature(
            serialized=self.mn2_serialized_signature)

        signatures_dict = {
            "artist": {artist_signature.pastelid: artist_signature.signature},
            "mn2": {mn2_signature.pastelid: mn2_signature.signature},
            "mn3": {mn3_signature.pastelid: mn3_signature.signature}
        }

        # write final ticket into blockchain
        art_ticket_data = {
            'cnode_package': ticket.serialize_base64(),
            'signatures_dict': signatures_dict,
            'key1': ticket.base64_imagedatahash,  # artist_signature.pastelid,
            'key2': ticket.base64_imagedatahash,
            'fee': int(self.localfee)
        }

        bc_response = get_blockchain_connection().register_art_ticket(**art_ticket_data)
        return bc_response


# FIXME: probably this field should be stored in DB (if we need them at all). then were in old implementation
# self.chunkid = chunkid
# self.verified = False
# self.is_ours = False
# self.last_fetch_time = None


class Chunk(Model):
    chunk_id = CharField(unique=True)
    image_hash = BlobField()
    indexed = BooleanField(default=False)  # to track fresh added chunks, and calculate XOR distances for them.
    confirmed = BooleanField(default=False)  # indicates if chunk ID is contained in one of confirmed registration tickets
    stored = BooleanField(default=False)

    class Meta:
        database = MASTERNODE_DB
        table_name = 'chunk'

    @classmethod
    def create_from_hash(cls, chunkhash, artwork_hash, stored=False):
        chunkhash_int = bytes_to_chunkid(chunkhash)
        return Chunk.create(chunk_id=str(chunkhash_int), image_hash=artwork_hash, stored=stored)

    @classmethod
    def get_by_hash(cls, chunkhash):
        chunkhash_int = bytes_to_chunkid(chunkhash)
        return Chunk.get(chunk_id=str(chunkhash_int))


class Masternode(Model):
    ext_address = CharField(unique=True)  # ip:port
    pastel_id = CharField(unique=True)
    active = BooleanField(default=True)  # optionally disable masternode

    class Meta:
        database = MASTERNODE_DB
        table_name = 'masternode'

    def get_rpc_client(self):
        ip, py_rpc_port = self.ext_address.split(':')
        rpc_client = RPCClient(self.pastel_id, ip, py_rpc_port)
        return rpc_client

    @classmethod
    def get_active_nodes(cls):
        return Masternode.select().where(Masternode.active == True)


class ChunkMnDistance(Model):
    chunk = ForeignKeyField(Chunk, on_delete='CASCADE')
    masternode = ForeignKeyField(Masternode, on_delete='CASCADE')
    distance = CharField()
    # TODO: actually we'll store very long integers here (64 bytes). But sqlite maximum integer
    #  size is 4 or 8 byte, which is insufficient. As we need to order by this field as it was an integer - need to
    #  make sure that all characters will be the same length, appended by zeros from the left if required.

    class Meta:
        database = MASTERNODE_DB
        table_name = 'chunkmndistance'


class ChunkMnRanked(Model):
    """
    Table for keeping top `Settings.REPLICATION_FACTOR` masternodes for each chunk.
    Content is completely removed and recalculated on each MN add/remove.
    Content is added when new chunks added.
    """
    chunk = ForeignKeyField(Chunk, on_delete='CASCADE')
    masternode = ForeignKeyField(Masternode, on_delete='CASCADE')
    rank = IntegerField()

    class Meta:
        database = MASTERNODE_DB
        table_name = 'chunkmnranked'


class ActivationTicket(Model):
    txid = CharField(unique=True)
    height = IntegerField()

    class Meta:
        database = MASTERNODE_DB
        table_name = 'act_ticket'


# TODO: when adding new model - add it to the following list as well. it's used for table creation.
DB_MODELS = [Regticket, Chunk, Masternode, ChunkMnDistance, ChunkMnRanked, ActivationTicket]
