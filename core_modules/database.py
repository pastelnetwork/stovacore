from decimal import Decimal

from peewee import Model, SqliteDatabase, BlobField, DateTimeField, DecimalField, BooleanField, IntegerField, CharField

from core_modules.settings import NetWorkSettings
from core_modules.ticket_models import RegistrationTicket

db = SqliteDatabase(NetWorkSettings.MN_DATABASE_FILE)

REGTICKET_STATUS_CREATED = 0
REGTICKET_STATUS_ERROR = -1
REGTICKET_STATUS_PLACED_ON_BLOCKCHAIN = 1

REGTICKET_STATUS_CHOICES = ((REGTICKET_STATUS_CREATED, 'Created'),
                            (REGTICKET_STATUS_ERROR, 'Error'),
                            (REGTICKET_STATUS_PLACED_ON_BLOCKCHAIN, 'Placed on blockchain'),)


class Regticket(Model):
    upload_code = BlobField(unique=True)
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

    class Meta:
        database = db
        table_name = 'regticket'

    def __is_burn_10_tx_height_valid(self, txid):
        regticket = RegistrationTicket(serialized=self.regticket)
        raw_tx_data = mnd.blockchain.getrawtransaction(txid, verbose=1)
        if not raw_tx_data:
            self.__errors.append('Burn 10% txid is invalid')
            return False

        if raw_tx_data['expiryheight'] < regticket.blocknum:
            self.__errors.append('Fee transaction is older then regticket.')
            return False

    def __is_burn_10_tx_amount_valid(self, txid):
        networkfee_result = mnd.blockchain.getnetworkfee()
        networkfee = networkfee_result['networkfee']
        tx_amounts = []
        raw_tx_data = mnd.blockchain.getrawtransaction(txid, verbose=1)
        for vout in raw_tx_data['vout']:
            tx_amounts.append(vout['value'])

        if self.localfee is not None:
            # we're main masternode (MN0)
            valid = False
            for tx_amount in tx_amounts:
                if self.localfee * Decimal(
                        '0.099') <= tx_amount <= self.localfee * Decimal('0.101'):
                    valid = True
                    break
            if not valid:
                self.__errors.append('Wrong fee amount')
                return False
            self.is_valid_mn0 = True
            self.save()
            return True
        else:
            # we're MN1 or MN2
            # we don't know exact MN0 fee, but it should be almost equal to the networkfee
            valid = False
            for tx_amount in tx_amounts:
                if networkfee * 0.09 <= tx_amount <= networkfee * 0.11:
                    valid = True
                    break
            if not valid:
                self.__errors.append('Payment amount differs with 10% of fee size.')
                return False
            else:
                return True

    def is_burn_tx_valid(self, txid):
        self.__errors = []
        if self.__is_burn_10_tx_height_valid(txid) and self.__is_burn_10_tx_amount_valid(txid):
            return True, None
        else:
            self.delete()
            return False, self.__errors

# FIXME: probably this field should be stored in DB (if we need them at all). then were in old implementation
# self.chunkid = chunkid
# self.verified = False
# self.is_ours = False
# self.last_fetch_time = None


class Chunk(Model):
    chunk_id = CharField(unique=True)
    image_hash = BlobField()

    class Meta:
        database = db
        table_name = 'chunk'


class Masternode(Model):
    ext_address = CharField(unique=True)  # ip:port
    pastel_id = CharField(unique=True)

    class Meta:
        database = db
        table_name = 'masternode'
