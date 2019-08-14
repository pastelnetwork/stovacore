import asyncio
import random
from decimal import Decimal

import time
import uuid

import bitcoinrpc
from bitcoinrpc.authproxy import JSONRPCException

from core_modules.blackbox_modules.luby import decode as luby_decode, NotEnoughChunks
from core_modules.blockchain import BlockChain
from core_modules.chainwrapper import ChainWrapper
from core_modules.http_rpc import RPCException
from core_modules.masternode_ticketing import IDRegistrationClient, TransferRegistrationClient, \
    TradeRegistrationClient
from core_modules.masternode_ticketing import FinalIDTicket, FinalTradeTicket, FinalTransferTicket, \
    FinalActivationTicket, FinalRegistrationTicket
from core_modules.logger import initlogging
from core_modules.helpers import hex_to_chunkid, bytes_from_hex, require_true
from wallet.art_registration_client import ArtRegistrationClient
from wallet.client_node_manager import ClientNodeManager
from wallet.database import RegticketDB
from wallet.settings import BURN_ADDRESS


class DjangoInterface:
    # TODO: privkey, pubkey - they're wallet's PastelID keys.
    # TODO: nodenum - probably we don't need as this code will not be run by node - it will be run only by wallet
    # TODO: all other fields probably not needed - need to review how they're used
    def __init__(self, privkey, pubkey, artregistry, chunkmanager, aliasmanager):

        self.__logger = initlogging('Wallet interface', __name__)

        self.__privkey = privkey
        self.__pubkey = pubkey

        self.__artregistry = artregistry
        self.__chunkmanager = chunkmanager
        self.__blockchain = self.__connect_to_daemon()
        self.__chainwrapper = ChainWrapper(None, self.__blockchain, self.__artregistry)
        self.__aliasmanager = aliasmanager
        self.__nodemanager = ClientNodeManager(self.__privkey, self.__pubkey,
                                               self.__blockchain)

        self.__active_tasks = {}

    def __connect_to_daemon(self):
        while True:
            blockchain = BlockChain(user='rt',
                                    password='rt',
                                    ip='127.0.0.1',
                                    rpcport=19932)
            try:
                blockchain.getwalletinfo()
            except (ConnectionRefusedError, bitcoinrpc.authproxy.JSONRPCException) as exc:
                self.__logger.debug("Exception %s while getting wallet info, retrying..." % exc)
                time.sleep(0.5)
            else:
                self.__logger.debug("Successfully connected to daemon!")
                break
        return blockchain

    def register_rpcs(self, rpcserver):
        rpcserver.add_callback("DJANGO_REQ", "DJANGO_RESP", self.process_django_request, coroutine=True,
                               allowed_pubkey=self.__django_pubkey)

    async def run_django_tasks_forever(self):
        while True:
            await asyncio.sleep(1)

            for future in self.__active_tasks.values():
                if not future.done():
                    try:
                        await future
                    except Exception as exc:
                        self.__logger.exception("Exception received in %s" % future)

    def __defer_execution(self, future):
        identifier = str(uuid.uuid4())
        self.__active_tasks[identifier] = future
        return identifier

    async def process_django_request(self, data):
        rpcname = data[0]
        args = data[1:]

        if rpcname == "get_info":
            return self.__get_infos()
        elif rpcname == "ping_masternodes":
            return await self.__ping_masternodes()
        elif rpcname == "get_chunk":
            return await self.__get_chunk_id(args[0])
        elif rpcname == "browse":
            return self.__browse(args[0])
        elif rpcname == "get_wallet_info":
            return self.__get_wallet_info(args[0])
        elif rpcname == "send_to_address":
            return self.__send_to_address(*args)
        elif rpcname == "register_image":
            return await self.__register_image(*args)
        elif rpcname == "get_identities":
            return self.__get_identities()
        elif rpcname == "register_identity":
            return self.__register_identity(args[0])
        elif rpcname == "execute_console_command":
            return self.__execute_console_command(args[0], args[1:])
        elif rpcname == "explorer_get_chaininfo":
            return self.__explorer_get_chaininfo()
        elif rpcname == "explorer_get_block":
            return self.__explorer_get_block(args[0])
        elif rpcname == "explorer_gettransaction":
            return self.__explorer_gettransaction(args[0])
        elif rpcname == "explorer_getaddresses":
            return self.__explorer_getaddresses(args[0])
        elif rpcname == "get_artworks_owned_by_me":
            return self.__get_artworks_owned_by_me()
        elif rpcname == "get_my_trades_for_artwork":
            return self.__get_my_trades_for_artwork(args[0])
        elif rpcname == "register_transfer_ticket":
            return self.__register_transfer_ticket(*args)
        elif rpcname == "get_artwork_info":
            return self.__get_artwork_info(args[0])
        elif rpcname == "register_trade_ticket":
            future = asyncio.ensure_future(self.__register_trade_ticket(*args))
            return self.__defer_execution(future)
        elif rpcname == "download_image":
            return await self.__download_image(*args)
        elif rpcname == "list_background_tasks":
            tasks = []
            for identifier, future in self.__active_tasks.items():
                exception = None
                if future.done():
                    exception = future.exception()

                    if exception is not None:
                        try:
                            raise exception
                        except Exception as exc:
                            self.__logger.exception("A background task has failed: %s" % (exc))

                d = {
                    "identifier": identifier,
                    "done": future.done(),
                    "exception": str(exception),
                }
                tasks.append(d)
            return tasks
        elif rpcname == "get_future_result":
            identifier = args[0]
            future = self.__active_tasks.get(identifier)
            return future.result()
        else:
            raise ValueError("Invalid RPC: %s" % rpcname)

    def __get_infos(self):
        infos = {}
        for name in ["getblockchaininfo", "getmempoolinfo", "gettxoutsetinfo", "getmininginfo",
                     "getnetworkinfo", "getpeerinfo", "getwalletinfo"]:
            infos[name] = getattr(self.__blockchain, name)()

        infos["mnsync"] = self.__blockchain.mnsync("status")
        return infos

    async def __ping_masternodes(self):
        masternodes = self.__nodemanager.get_all()

        tasks = []
        for mn in masternodes:
            tasks.append(mn.send_rpc_ping(b'PING'))

        ret = await asyncio.gather(*tasks)
        return ret

    async def __get_chunk_id(self, chunkid_hex):
        await asyncio.sleep(0)
        chunkid = hex_to_chunkid(chunkid_hex)

        chunk_data = None

        # find MNs that have this chunk
        owners = list(self.__aliasmanager.find_other_owners_for_chunk(chunkid))
        random.shuffle(owners)

        for owner in owners:
            mn = self.__nodemanager.get(owner)

            chunk_data = await mn.send_rpc_fetchchunk(chunkid)

            if chunk_data is not None:
                break

        return chunk_data

    def __browse(self, txid):
        artworks = self.__artregistry.get_all_artworks()

        tickets, ticket = [], None
        if txid == "":
            for txid, ticket in self.__chainwrapper.all_ticket_iterator():
                if type(ticket) == FinalIDTicket:
                    tickets.append((txid, "identity", ticket.to_dict()))
                if type(ticket) == FinalRegistrationTicket:
                    tickets.append((txid, "regticket", ticket.to_dict()))
                if type(ticket) == FinalActivationTicket:
                    tickets.append((txid, "actticket", ticket.to_dict()))
                if type(ticket) == FinalTransferTicket:
                    tickets.append((txid, "transticket", ticket.to_dict()))
                if type(ticket) == FinalTradeTicket:
                    tickets.append((txid, "tradeticket", ticket.to_dict()))
        else:
            # get and process ticket as new node
            ticket = self.__chainwrapper.retrieve_ticket(txid)

        if ticket is not None:
            ticket = ticket.to_dict()
        return artworks, tickets, ticket

    def __get_wallet_info(self, pubkey):
        listunspent = self.__blockchain.listunspent()
        receivingaddress = self.__blockchain.getaccountaddress("")
        balance = self.__blockchain.getbalance()
        collateral_utxos = list(self.__artregistry.get_all_collateral_utxo_for_pubkey(pubkey))
        return listunspent, receivingaddress, balance, collateral_utxos

    def __send_to_address(self, address, amount, comment=""):
        try:
            result = self.__blockchain.sendtoaddress(address, amount, public_comment=comment)
        except JSONRPCException as exc:
            return str(exc)
        else:
            return result

    async def register_image(self, image_field, image_data):
        # get the registration object
        artreg = ArtRegistrationClient(self.__privkey, self.__pubkey, self.__chainwrapper, self.__nodemanager)

        # register image
        # TODO: fill these out properly
        task = artreg.register_image(
            image_data=image_data,
            artist_name="Example Artist",
            artist_website="exampleartist.com",
            artist_written_statement="This is only a test",
            artwork_title=image_field,
            artwork_series_name="Examples and Tests collection",
            artwork_creation_video_youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            artwork_keyword_set="example, testing, sample",
            total_copies=10
        )

        result = await task
        actticket_txid = result
        final_actticket = self.__chainwrapper.retrieve_ticket(actticket_txid, validate=True)
        return actticket_txid, final_actticket.to_dict()

    async def image_registration_step_2(self, title, image_data):
        artreg = ArtRegistrationClient(self.__privkey, self.__pubkey, self.__chainwrapper, self.__nodemanager)

        result = await artreg.get_workers_fee(
            image_data=image_data,
            artist_name="Example Artist",
            artist_website="exampleartist.com",
            artist_written_statement="This is only a test",
            artwork_title=title,
            artwork_series_name="Examples and Tests collection",
            artwork_creation_video_youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            artwork_keyword_set="example, testing, sample",
            total_copies=10
        )

        return result

    async def image_registration_step_3(self, regticket_id):
        artreg = ArtRegistrationClient(self.__privkey, self.__pubkey, self.__chainwrapper, self.__nodemanager)

        success, err = await artreg.send_regticket_to_mn2_mn3(regticket_id)
        if not success:
            return {'status': 'ERROR', 'msg': err}
        regticket_db = RegticketDB.get(RegticketDB.id == regticket_id)
        amount = "{0:.5f}".format(regticket_db.worker_fee * 0.1)
        # burn 10% of worker's fee
        # TODO: current BURN_ADDRESS is taken from MN3. Pick another burn address.
        self.__logger.warn('Sending to BURN_ADDRESS, amount: {}'.format(amount))
        burn_10_percent_txid = self.__send_to_address(BURN_ADDRESS, amount)
        self.__logger.warn('Burn txid is {}'.format(burn_10_percent_txid))
        # store txid in DB
        regticket_db.burn_tx_id = burn_10_percent_txid
        regticket_db.save()

        mn0, mn1, mn2 = self.__nodemanager.get_masternode_ordering(regticket_db.blocknum)

        async def send_txid_10_req_to_mn(mn, data):
            """
            Here we push ticket to given masternode, receive upload_code, then push image.
            Masternode will return fee, but we ignore it here.
            :return (result, status)
            """
            try:
                result = await mn.call_masternode("TXID_10_REQ", "TXID_10_RESP",
                                                  data)
                return result, True
            except RPCException as ex:
                return str(ex), False

        mn0_response, mn1_response, mn2_response = await asyncio.gather(
            send_txid_10_req_to_mn(mn0, [burn_10_percent_txid, regticket_db.upload_code_mn0]),
            send_txid_10_req_to_mn(mn1, [burn_10_percent_txid, regticket_db.upload_code_mn1]),
            send_txid_10_req_to_mn(mn2, [burn_10_percent_txid, regticket_db.upload_code_mn2]),
            return_exceptions=True
        )
        self.__logger.warn('MN0: {}'.format(mn0_response))
        self.__logger.warn('MN1: {}'.format(mn1_response))
        self.__logger.warn('MN2: {}'.format(mn2_response))
        return {
            'status': 'SUCCESS',
            'mn_data': {
                'mn0': {'status': 'SUCCESS' if mn0_response[1] else 'ERROR',
                        'msg': mn0_response[0]},
                'mn1': {'status': 'SUCCESS' if mn1_response[1] else 'ERROR',
                        'msg': mn1_response[0]},
                'mn2': {'status': 'SUCCESS' if mn2_response[1] else 'ERROR',
                        'msg': mn2_response[0]}
            }
        }

    def __get_identities(self):
        addresses = []
        for unspent in self.__blockchain.listunspent():
            if unspent["address"] not in addresses:
                addresses.append(unspent["address"])

        identity_txid, identity_ticket = self.__chainwrapper.get_identity_ticket(self.__pubkey)
        all_identities = list(
            (txid, ticket.to_dict()) for txid, ticket in self.__chainwrapper.get_tickets_by_type("identity"))
        return addresses, all_identities, identity_txid, {} if identity_ticket is None else identity_ticket.to_dict()

    def __register_identity(self, address):
        regclient = IDRegistrationClient(self.__privkey, self.__pubkey, self.__chainwrapper)
        regclient.register_id(address)

    def __execute_console_command(self, cmdname, cmdargs):
        command_rpc = getattr(self.__blockchain, cmdname)
        try:
            result = command_rpc(*cmdargs)
        except JSONRPCException as exc:
            return False, "EXCEPTION: %s" % exc
        else:
            return True, result

    def __explorer_get_chaininfo(self):
        return self.__blockchain.getblockchaininfo()

    def __explorer_get_block(self, blockid):
        blockcount, block = None, None

        blockcount = self.__blockchain.getblockcount() - 1
        if blockid != "":
            try:
                block = self.__blockchain.getblock(blockid)
            except JSONRPCException:
                block = None

        return blockcount, block

    def __explorer_gettransaction(self, transactionid):
        transaction = None
        try:
            if transactionid == "":
                transaction = self.__blockchain.listsinceblock()["transactions"][-1]
            else:
                transaction = self.__blockchain.gettransaction(transactionid)
        except JSONRPCException:
            pass
        return transaction

    def __explorer_getaddresses(self, addressid):
        transactions = None
        try:
            if addressid != "":
                transactions = self.__blockchain.listunspent(1, 999999999, [addressid])
            else:
                transactions = self.__blockchain.listunspent(1, 999999999)
        except JSONRPCException:
            pass
        return transactions

    def __get_artworks_owned_by_me(self):
        return self.__artregistry.get_art_owned_by(self.__pubkey)

    def __get_my_trades_for_artwork(self, artid_hex):
        artid = bytes_from_hex(artid_hex)
        return self.__artregistry.get_my_trades_for_artwork(self.__pubkey, artid)

    def __register_transfer_ticket(self, recipient_pubkey_hex, imagedata_hash_hex, copies):
        recipient_pubkey = bytes_from_hex(recipient_pubkey_hex)
        imagedata_hash = bytes_from_hex(imagedata_hash_hex)
        transreg = TransferRegistrationClient(self.__privkey, self.__pubkey, self.__chainwrapper, self.__artregistry)
        transreg.register_transfer(recipient_pubkey, imagedata_hash, copies)

    def __get_artwork_info(self, artid_hex):
        artid = bytes_from_hex(artid_hex)

        ticket = self.__artregistry.get_ticket_for_artwork(artid)
        if ticket is not None:
            # extract the regticket
            regticket = self.__chainwrapper.retrieve_ticket(ticket.ticket.registration_ticket_txid)
            ticket = regticket.ticket.to_dict()
        else:
            ticket = {}

        art_owners = self.__artregistry.get_art_owners(artid)

        open_tickets, closed_tickets = [], []
        for tradeticket in self.__artregistry.get_art_trade_tickets(artid):
            created, txid, done, status, tickettype, regticket = tradeticket
            if done is not True:
                open_tickets.append(tradeticket)
            else:
                closed_tickets.append(tradeticket)

        return ticket, art_owners, open_tickets, closed_tickets

    async def __register_trade_ticket(self, imagedata_hash_hex, tradetype, copies, price, expiration):
        imagedata_hash = bytes_from_hex(imagedata_hash_hex)

        # We do this here to prevent creating a ticket we know now as invalid. However anything
        # might happen before this ticket makes it to the network, so this check can't be put in validate()
        if tradetype == "ask":
            # make sure we have enough remaining copies left if we are asking
            require_true(self.__artregistry.enough_copies_left(imagedata_hash,
                                                               self.__pubkey,
                                                               copies))
        else:
            # not a very thorough check, as we might have funds locked in collateral addresses
            # if this is the case we will fail later when trying to move the funds
            if self.__blockchain.getbalance() < price:
                raise ValueError("Not enough money in wallet!")

        # watched address is the address we are using to receive the funds in asks and send the collateral to in bids
        watched_address = self.__blockchain.getnewaddress()

        transreg = TradeRegistrationClient(self.__privkey, self.__pubkey, self.__blockchain, self.__chainwrapper,
                                           self.__artregistry)
        await transreg.register_trade(imagedata_hash, tradetype, watched_address, copies, price, expiration)

    async def __download_image(self, artid_hex):
        artid = bytes_from_hex(artid_hex)

        ticket = self.__artregistry.get_ticket_for_artwork(artid)
        if ticket is not None:
            finalregticket = self.__chainwrapper.retrieve_ticket(ticket.ticket.registration_ticket_txid)
            regticket = finalregticket.ticket
            lubyhashes = regticket.lubyhashes.copy()

            lubychunks = []
            while True:
                # fetch chunks 5 at a time
                # TODO: maybe turn this into a parameter or a settings variable
                rpcs = []
                while len(rpcs) < 15 and len(lubyhashes) > 0:
                    lubyhash = lubyhashes.pop(0)
                    rpcs.append(self.__get_chunk_id(lubyhash.hex()))

                # if we ran out of chunks, abort
                if len(rpcs) == 0:
                    break

                chunks = await asyncio.gather(*rpcs)
                for chunk in chunks:
                    lubychunks.append(chunk)

                self.__logger.debug("Fetched luby chunks, total chunks: %s" % len(lubychunks))

                try:
                    decoded = luby_decode(lubychunks)
                except NotEnoughChunks:
                    self.__logger.debug("Luby decode failed with NotEnoughChunks!")
                else:
                    self.__logger.debug("Luby decode successful!")
                    return decoded

            self.__logger.warning("Could not get enough Luby chunks to reconstruct image!")
            raise RuntimeError("Could not get enough Luby chunks to reconstruct image!")
