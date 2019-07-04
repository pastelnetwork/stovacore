import asyncio
import random
from decimal import Decimal

from bitcoinrpc.authproxy import JSONRPCException

from core_modules.logger import initlogging
from core_modules.helpers import bytes_from_hex, bytes_to_hex
from core_modules.ticket_models import FinalIDTicket, FinalActivationTicket, FinalRegistrationTicket,\
    FinalTransferTicket, FinalTradeTicket
from core_modules.settings import NetWorkSettings


class BlockChainTicket:
    def __init__(self, tickettype, data):
        self.tickettype = tickettype
        self.data = data


class ChainWrapper:
    def __init__(self, nodenum, blockchain, artregistry):
        self.__logger = initlogging(nodenum, __name__)
        self.__blockchain = blockchain
        self.__artregistry = artregistry

        # nonces stores the nonces we have already seen
        self.__nonces = set()

    def masternode_workers(self, blocknum=None):
        return self.__blockchain.masternode_workers(blocknum)

    def get_tickets_by_type(self, tickettype):
        if tickettype not in ["identity", "regticket", "actticket", "transticket", "tradeticket"]:
            raise ValueError("%s is not a valid ticket type!" % tickettype)

        for txid, ticket in self.all_ticket_iterator():
            if tickettype == "identity":
                if type(ticket) == FinalIDTicket:
                    yield txid, ticket
            elif tickettype == "regticket":
                if type(ticket) == FinalRegistrationTicket:
                    yield txid, ticket
            elif tickettype == "actticket":
                if type(ticket) == FinalActivationTicket:
                    yield txid, ticket
            elif tickettype == "transticket":
                if type(ticket) == FinalTransferTicket:
                    yield txid, ticket
            elif tickettype == "tradeticket":
                if type(ticket) == FinalTradeTicket:
                    yield txid, ticket

    def get_identity_ticket(self, pubkey):
        for txid, ticket in self.get_tickets_by_type("identity"):
            if ticket.ticket.public_key == pubkey:
                return txid, ticket
        return None, None

    def get_block_distance(self, atxid, btxid):
        # TODO: clean up this interface
        if type(atxid) == bytes:
            atxid = bytes_to_hex(atxid)
        if type(btxid) == bytes:
            btxid = bytes_to_hex(btxid)

        block_a = self.__blockchain.getblock(atxid)
        block_b = self.__blockchain.getblock(btxid)
        height_a = int(block_a["height"])
        height_b = int(block_b["height"])
        return abs(height_a-height_b)

    def get_last_block_hash(self):
        return self.__blockchain.getbestblockhash()

    def get_last_block_number(self):
        return self.__blockchain.getblockcount()

    def store_ticket(self, ticket):
        if type(ticket) == FinalIDTicket:
            identifier = b'idticket'
        elif type(ticket) == FinalRegistrationTicket:
            identifier = b'regticket'
        elif type(ticket) == FinalActivationTicket:
            identifier = b'actticket'
        elif type(ticket) == FinalTransferTicket:
            identifier = b'transticket'
        elif type(ticket) == FinalTradeTicket:
            identifier = b'tradeticket'
        else:
            raise TypeError("Ticket type invalid: %s" % type(ticket))

        encoded_data = identifier + ticket.serialize()

        return self.__blockchain.store_data_in_utxo(encoded_data)

    def retrieve_ticket(self, txid, validate=False):
        try:
            raw_ticket_data = self.__blockchain.retrieve_data_from_utxo(txid)
        except JSONRPCException as exc:
            if exc.code == -8:
                # parameter 1 must be hexadecimal string
                return None
            else:
                raise

        if raw_ticket_data.startswith(b'idticket'):
            ticket = FinalIDTicket(serialized=raw_ticket_data[len(b'idticket'):])
            if validate:
                ticket.validate(self)
        elif raw_ticket_data.startswith(b'regticket'):
            ticket = FinalRegistrationTicket(serialized=raw_ticket_data[len(b'regticket'):])
            if validate:
                ticket.validate(self)
        elif raw_ticket_data.startswith(b'actticket'):
            ticket = FinalActivationTicket(serialized=raw_ticket_data[len(b'actticket'):])
            if validate:
                ticket.validate(self)
        elif raw_ticket_data.startswith(b'transticket'):
            ticket = FinalTransferTicket(serialized=raw_ticket_data[len(b'transticket'):])
            if validate:
                ticket.validate(self)
        elif raw_ticket_data.startswith(b'tradeticket'):
            ticket = FinalTradeTicket(serialized=raw_ticket_data[len(b'tradeticket'):])
            if validate:
                ticket.validate(self)
        else:
            raise ValueError("TXID %s is not a valid ticket: %s" % (txid, raw_ticket_data))

        return ticket

    def all_ticket_iterator(self):
        for txid in self.__blockchain.search_chain():
            try:
                ticket = self.retrieve_ticket(txid)
            except Exception as exc:
                # self.__logger.debug("ERROR parsing txid %s: %s" % (txid, exc))
                continue
            else:
                # if we didn't manage to get a good ticket back (bad txid)
                if ticket is None:
                    continue
            yield txid, ticket

    def get_transactions_for_block(self, blocknum, confirmations=NetWorkSettings.REQUIRED_CONFIRMATIONS):
        for txid in self.__blockchain.get_txids_for_block(blocknum, confirmations):
            try:
                ticket = self.retrieve_ticket(txid, validate=False)
            except JSONRPCException as exc:
                continue
            except Exception as exc:
                yield txid, "transaction", self.__blockchain.getrawtransaction(txid, 1)
            else:
                # validate the tickets, only return them if we ran the validator
                if type(ticket) == FinalActivationTicket:
                    ticket.validate(self)
                elif type(ticket) == FinalTransferTicket:
                    ticket.validate(self)
                elif type(ticket) == FinalTradeTicket:
                    ticket.validate(self)
                else:
                    continue

                ret = txid, "ticket", ticket

                # TODO: implement an on-disk validation cache, so we can speed up this process and
                # avoid re-parsing the tickets on each run

                # mark nonce as used
                self.__nonces.add(ticket.nonce)

                yield ret

    async def move_funds_to_new_wallet(self, my_public_key, collateral_address, copies, price):
        amount_to_send = Decimal(copies) * Decimal(price)

        # make sure we sleep
        await asyncio.sleep(0)

        # get all my trade tickets that need collateral
        locked_utxos = self.__artregistry.get_all_collateral_utxo_for_pubkey(my_public_key)

        eligible_unspent = []
        for unspent in self.__blockchain.listunspent():
            if unspent["spendable"] is True\
            and unspent["confirmations"] > NetWorkSettings.REQUIRED_CONFIRMATIONS_FOR_TRADE_UTXO\
            and unspent["txid"] not in locked_utxos:
                eligible_unspent.append(unspent)

        balance = sum((x["amount"] for x in eligible_unspent))
        if amount_to_send > balance:
            raise ValueError("Not enough coins available for transaction: %s / %s" % (amount_to_send, balance))

        # create a change address
        change_address = self.__blockchain.getnewaddress()

        # create raw transaction
        raw_transaction = self.__create_raw_transaction(eligible_unspent,
                                                        [(collateral_address, amount_to_send)], change_address)

        signed_raw_transaction = self.__blockchain.signrawtransaction(raw_transaction)

        self.__logger.debug("Signed raw transaction: %s" % signed_raw_transaction)

        if hasattr(signed_raw_transaction, "errors"):
            raise ValueError("Errors in signed transaction: %s" % signed_raw_transaction["errors"])

        txid = self.__blockchain.sendrawtransaction(signed_raw_transaction["hex"])

        self.__logger.debug("Published collateral transaction with txid: %s" % txid)

        while True:
            transaction_info = self.__blockchain.gettransaction(txid)
            if transaction_info["confirmations"] < NetWorkSettings.REQUIRED_CONFIRMATIONS_FOR_TRADE_UTXO:
                await asyncio.sleep(1)
            else:
                break

        return txid

    def __create_raw_transaction(self, eligible_unspent, addresses, change_address):
        # shuffle eligible utxos
        random.shuffle(eligible_unspent)

        # how many kbytes we want to produce at most - we pay for every byte, so we set it low
        kbytes_paid = 1
        fees = kbytes_paid * NetWorkSettings.FEEPERKB  # this would cover up to 1 kbyte

        # get total amount
        amount_to_send = Decimal('0')
        for address, amount in addresses:
            amount_to_send += amount

        # consume utxos until we have enough funds with fees
        total_in = Decimal()
        inputs = []
        outputs = {}
        eligible_unspent_copy = eligible_unspent.copy()
        while total_in < amount_to_send + fees:
            transaction = eligible_unspent_copy.pop(0)
            total_in += transaction["amount"]
            inputs.append({
                "txid": transaction["txid"],
                "vout": transaction["vout"],
            })

        for address, amount in addresses:
            outputs[address] = amount

        outputs[change_address] = total_in - amount_to_send - fees

        self.__logger.debug("Paying %s to %s, change %s to %s from a total of %s, with fees: %s" % (
            amount_to_send, addresses, outputs[change_address], change_address, total_in, fees))

        rawtrans = self.__blockchain.createrawtransaction(inputs, outputs)

        # we calculate the final transaction size + 128bytes (for signatures)
        # If we are above this limit we fail. If this happens there are a large number of utxos with small
        # amounts in them, and we ran out of space. Raise kbytes_paid.
        total_bytes_used = len(rawtrans) / 2 / 1024  # /2 because it's in hex
        if total_bytes_used > kbytes_paid * 1024:
            raise ValueError("Final transaction size is larger than kbytes paid for: %s > %s. Consolidate your utxos!"
                             % (total_bytes_used, kbytes_paid * 1024))

        # check rawtrans to make sure things add up
        decoded = self.__blockchain.decoderawtransaction(rawtrans)

        # sum up ins
        total_in = Decimal()
        for vin in decoded["vin"]:
            found = False
            for unspent in eligible_unspent:
                if unspent["txid"] == vin["txid"] and unspent["vout"] == vin["vout"]:
                    total_in += unspent["amount"]
                    found = True
            if not found:
                raise ValueError("TXID %s not found in eligible_unspent: %s" % (
                    vin["txid"], [x["txid"] for x in eligible_unspent]))

        # sum up outs
        total_out = Decimal()
        for vout in decoded["vout"]:
            total_out += vout["value"]

        # make sure everything adds up
        tmp_fees = total_in - total_out
        self.__logger.debug("Total in: %s, total out: %s, fees: %s" % (total_in, total_out, tmp_fees))

        # we have to make sure that fees are reasonable
        if tmp_fees > fees:
            raise ValueError("Invalid fees in decoded transaction: %s > %s, decoded transaction: %s" % (
                tmp_fees, fees, decoded))

        return rawtrans

    def valid_nonce(self, nonce):
        return nonce not in self.__nonces
