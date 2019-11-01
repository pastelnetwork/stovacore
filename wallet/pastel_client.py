import asyncio
import random
import uuid

from bitcoinrpc.authproxy import JSONRPCException

from cnode_connection import get_blockchain_connection
from core_modules.artregistry import ArtRegistry
from core_modules.blackbox_modules.luby import decode as luby_decode, NotEnoughChunks
from core_modules.chainwrapper import ChainWrapper
from core_modules.http_rpc import RPCException, RPCClient
from core_modules.masternode_ticketing import IDRegistrationClient, TransferRegistrationClient, \
    TradeRegistrationClient
from core_modules.masternode_ticketing import FinalIDTicket, FinalTradeTicket, FinalTransferTicket, \
    FinalActivationTicket, FinalRegistrationTicket
from core_modules.logger import initlogging
from core_modules.helpers import bytes_from_hex, require_true, bytes_to_chunkid
from utils.utils import get_masternode_ordering
from wallet.art_registration_client import ArtRegistrationClient
from wallet.client_node_manager import ClientNodeManager
from wallet.database import RegticketDB
from wallet.settings import BURN_ADDRESS


def masternodes_by_distance_from_image(image_hash):
    # FIXME: hardcoded list for testing only
    # TODO: how should it behave:
    # - get masternodelist (with pastelid)
    # calculate some hash for each node based on pastelid
    # calculated distance between node hash and image_hash
    # return masternodes sorted by this hash
    masternodes = get_blockchain_connection().masternode_list().values()
    mn_clients = []
    for mn in masternodes:
        mn_clients.append(RPCClient(mn['extKey'], mn['extAddress'].split(':')[0], mn['extAddress'].split(':')[1]))
    return mn_clients


class PastelClient:
    def __init__(self, pastelid, passphrase):

        self.__logger = initlogging('Wallet interface', __name__)

        self.pastelid = pastelid
        self.passphrase = passphrase

        self.__artregistry = ArtRegistry()
        self.__chainwrapper = ChainWrapper(self.__artregistry)
        self.__nodemanager = ClientNodeManager()
        self.__active_tasks = {}

    def __defer_execution(self, future):
        identifier = str(uuid.uuid4())
        self.__active_tasks[identifier] = future
        return identifier

    def __send_to_address(self, address, amount, comment=""):
        try:
            result = get_blockchain_connection().sendtoaddress(address, amount, public_comment=comment)
        except JSONRPCException as exc:
            return str(exc)
        else:
            return result

    # Image registration methods
    async def register_image(self, image_field, image_data):
        # get the registration object
        artreg = ArtRegistrationClient(self.__chainwrapper)

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
        artreg = ArtRegistrationClient(self.__chainwrapper)

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
        artreg = ArtRegistrationClient(self.__chainwrapper)

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

        mn0, mn1, mn2 = get_masternode_ordering(regticket_db.blocknum)

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
        if mn0_response[1] and mn1_response[1] and mn2_response[1]:
            # all responses indicate success. Mn1 or mn2 response should container txid
            if 'txid' in mn1_response[0]:
                txid = mn1_response[0]['txid']
            elif 'txid' in mn2_response[0]:
                txid = mn2_response[0]['txid']
            else:
                raise Exception('Txid not found neither in mn1 nor in mn2 response!')
            return {'status': 'SUCCESS', 'txid': txid}
        else:
            # some error happened, return details
            return {
                'status': 'SUCCESS' if mn0_response[1] and mn1_response[1] and mn2_response[1] else 'ERROR',
                'mn_data': {
                    'mn0': {'status': 'SUCCESS' if mn0_response[1] else 'ERROR',
                            'msg': mn0_response[0]},
                    'mn1': {'status': 'SUCCESS' if mn1_response[1] else 'ERROR',
                            'msg': mn1_response[0]},
                    'mn2': {'status': 'SUCCESS' if mn2_response[1] else 'ERROR',
                            'msg': mn2_response[0]}
                }
            }

    async def download_image(self, image_hash):
        mn_rpc_clients = masternodes_by_distance_from_image(image_hash)
        image_data = None
        for mn in mn_rpc_clients:
            response = await mn.call_masternode("IMAGEDOWNLOAD_REQ", "IMAGEDOWNLOAD_RESP",
                                                {'image_hash': image_hash})
            if response['status'] == 'SUCCESS':
                image_data = response['image_data']
                break
        return image_data

    # TODO: Methods below are not currently used. Need to inspect and probably remove
    def __get_identities(self):
        addresses = []
        for unspent in get_blockchain_connection().listunspent():
            if unspent["address"] not in addresses:
                addresses.append(unspent["address"])

        identity_txid, identity_ticket = self.__chainwrapper.get_identity_ticket(self.__pubkey)
        all_identities = list(
            (txid, ticket.to_dict()) for txid, ticket in self.__chainwrapper.get_tickets_by_type("identity"))
        return addresses, all_identities, identity_txid, {} if identity_ticket is None else identity_ticket.to_dict()

    def __register_identity(self, address):
        regclient = IDRegistrationClient(self.__privkey, self.__pubkey, self.__chainwrapper)
        regclient.register_id(address)

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
            if get_blockchain_connection().getbalance() < price:
                raise ValueError("Not enough money in wallet!")

        # watched address is the address we are using to receive the funds in asks and send the collateral to in bids
        watched_address = get_blockchain_connection().getnewaddress()

        transreg = TradeRegistrationClient(self.__privkey, self.__pubkey, blockchain, self.__chainwrapper,
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
