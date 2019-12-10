import asyncio
import random
from decimal import Decimal


from core_modules.logger import initlogging
from core_modules.helpers import bytes_to_hex
from core_modules.settings import NetWorkSettings
from cnode_connection import get_blockchain_connection


class ChainWrapper:
    def __init__(self, artregistry):
        self.__logger = initlogging('', __name__)
        self.__artregistry = artregistry

        # nonces stores the nonces we have already seen
        self.__nonces = set()

    def get_block_distance(self, atxid, btxid):
        if type(atxid) == bytes:
            atxid = bytes_to_hex(atxid)
        if type(btxid) == bytes:
            btxid = bytes_to_hex(btxid)

        block_a = get_blockchain_connection().getblock(atxid)
        block_b = get_blockchain_connection().getblock(btxid)
        height_a = int(block_a["height"])
        height_b = int(block_b["height"])
        return abs(height_a-height_b)

    async def move_funds_to_new_wallet(self, my_public_key, collateral_address, copies, price):
        amount_to_send = Decimal(copies) * Decimal(price)

        # make sure we sleep
        await asyncio.sleep(0)

        # get all my trade tickets that need collateral
        locked_utxos = self.__artregistry.get_all_collateral_utxo_for_pubkey(my_public_key)

        eligible_unspent = []
        for unspent in get_blockchain_connection().listunspent():
            if unspent["spendable"] is True\
            and unspent["confirmations"] > NetWorkSettings.REQUIRED_CONFIRMATIONS_FOR_TRADE_UTXO\
            and unspent["txid"] not in locked_utxos:
                eligible_unspent.append(unspent)

        balance = sum((x["amount"] for x in eligible_unspent))
        if amount_to_send > balance:
            raise ValueError("Not enough coins available for transaction: %s / %s" % (amount_to_send, balance))

        # create a change address
        change_address = get_blockchain_connection().getnewaddress()

        # create raw transaction
        raw_transaction = self.__create_raw_transaction(eligible_unspent,
                                                        [(collateral_address, amount_to_send)], change_address)

        signed_raw_transaction = get_blockchain_connection().signrawtransaction(raw_transaction)

        self.__logger.debug("Signed raw transaction: %s" % signed_raw_transaction)

        if hasattr(signed_raw_transaction, "errors"):
            raise ValueError("Errors in signed transaction: %s" % signed_raw_transaction["errors"])

        txid = get_blockchain_connection().sendrawtransaction(signed_raw_transaction["hex"])

        self.__logger.debug("Published collateral transaction with txid: %s" % txid)

        while True:
            transaction_info = get_blockchain_connection().gettransaction(txid)
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

        rawtrans = get_blockchain_connection().createrawtransaction(inputs, outputs)

        # we calculate the final transaction size + 128bytes (for signatures)
        # If we are above this limit we fail. If this happens there are a large number of utxos with small
        # amounts in them, and we ran out of space. Raise kbytes_paid.
        total_bytes_used = len(rawtrans) / 2 / 1024  # /2 because it's in hex
        if total_bytes_used > kbytes_paid * 1024:
            raise ValueError("Final transaction size is larger than kbytes paid for: %s > %s. Consolidate your utxos!"
                             % (total_bytes_used, kbytes_paid * 1024))

        # check rawtrans to make sure things add up
        decoded = get_blockchain_connection().decoderawtransaction(rawtrans)

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
