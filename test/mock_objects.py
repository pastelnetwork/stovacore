import pprint

from collections import OrderedDict
from core_modules.helpers import get_cnode_digest_bytes, get_cnode_digest_hex, get_nodeid_from_pubkey, bytes_from_hex, bytes_to_hex


class DummyTicket:
    def serialize(self):
        return b'test data'

    def to_dict(self):
        return "DummyTicket"


class MockChainWrapper:
    def __init__(self):
        self.__storage = OrderedDict()

        # set up so that last_block_hash returns something meaningful
        self.store_ticket(DummyTicket())

    def all_ticket_iterator(self):
        for txid, ticket in self.__storage.items():
            yield txid, ticket

    def get_last_block_hash(self):
        return next(reversed(self.__storage.items()))[0]

    def get_block_distance(self, atxid, btxid):
        txids = list(self.__storage.keys())
        return abs(txids.index(atxid) - txids.index(btxid))

    def store_ticket(self, ticket):
        txid = get_cnode_digest_hex(ticket.serialize())
        self.__storage[txid] = ticket
        return txid

    def retrieve_ticket(self, txid):
        return self.__storage[txid]

    def debug_dump_storage(self):
        print("DEBUG DUMP")
        for txid, ticket in self.__storage.items():
            print(bytes_to_hex(txid), pprint.pformat(ticket.to_dict(), indent=4))

    def valid_nonce(self, nonce):
        return True
