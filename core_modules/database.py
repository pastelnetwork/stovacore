from peewee import (Model, SqliteDatabase, BlobField, DateTimeField, DecimalField, BooleanField, IntegerField,
                    CharField,
                    ForeignKeyField)

from core_modules.helpers import bytes_to_chunkid

db = SqliteDatabase(None)

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
        database = db
        table_name = 'regticket'


# FIXME: probably this field should be stored in DB (if we need them at all). then were in old implementation
# self.chunkid = chunkid
# self.verified = False
# self.is_ours = False
# self.last_fetch_time = None


class Chunk(Model):
    chunk_id = CharField(unique=True)
    image_hash = BlobField()
    indexed = BooleanField(default=False)  # to track fresh added chunks, and calculate XOR distances for them.
    confirmed = BooleanField(default=False)  # indicates if chunk ID is contained in one
    # of confirmed registration tickets

    class Meta:
        database = db
        table_name = 'chunk'

    @classmethod
    def create_from_hash(cls, chunkhash, artwork_hash):
        chunkhash_int = bytes_to_chunkid(chunkhash)
        Chunk.create(chunk_id=str(chunkhash_int), image_hash=artwork_hash)

    @classmethod
    def get_by_hash(cls, chunkhash):
        chunkhash_int = bytes_to_chunkid(chunkhash)
        return Chunk.get(chunk_id=str(chunkhash_int))


class Masternode(Model):
    ext_address = CharField(unique=True)  # ip:port
    pastel_id = CharField(unique=True)

    class Meta:
        database = db
        table_name = 'masternode'


class ChunkMnDistance(Model):
    chunk = ForeignKeyField(Chunk, on_delete='CASCADE')
    masternode = ForeignKeyField(Masternode, on_delete='CASCADE')
    distance = CharField()
    # TODO: actually we'll store very long integers here (64 bytes). But sqlite maximum integer
    #  size is 4 or 8 byte, which is insufficient. As we need to order by this field as it was an integer - need to
    #  make sure that all characters will be the same length, appended by zeros from the left if required.

    class Meta:
        database = db
        table_name = 'chunkmndistance'


DB_MODELS = [Regticket, Chunk, Masternode, ChunkMnDistance]
