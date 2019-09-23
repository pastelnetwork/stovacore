from core_modules.logger import initlogging
from cnode_connection import blockchain


class AutoTrader:
    def __init__(self, artregistry):
        self.__logger = initlogging('', __name__)
        self.__artregistry = artregistry
        self.__enabled = False

    def consummate_trades(self):
        if not self.__enabled:
            return

        # collect all transaction currently in the mempool
        mempool_transactions = set()
        for txid in blockchain.getrawmempool(verbose=False):
            transaction = blockchain.getrawtransaction(txid, 1)
            for vout in transaction["vout"]:
                if "addresses" not in vout["scriptPubKey"]:
                    continue

                if len(vout["scriptPubKey"]["addresses"]) > 1:
                    continue

                # valid transaction received, process value
                value = vout["value"]
                address = vout["scriptPubKey"]["addresses"][0]
                mempool_transactions.add((address, value))

        # check on all tickets requiring consummation from us
        for watched_address, total_price in self.__artregistry.get_trades_for_automatic_consummation():
            # if a valid transaction makes it onto the blockchain the trade will be consummated,
            # so we only need to check mempool here
            if (watched_address, total_price) in mempool_transactions:
                # this transaction already exists, do nothing
                continue

            # consummate
            blockchain.sendtoaddress(watched_address, total_price)
            self.__logger.debug("Consummating transaction: %s, price: %s" % (watched_address, total_price))

    def enable(self):
        self.__enabled = True

    def enabled(self):
        return self.__enabled
