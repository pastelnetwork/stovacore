import json

import asyncio
import os
import uuid

from bitcoinrpc.authproxy import JSONRPCException

from cnode_connection import get_blockchain_connection
from core_modules.rpc_client import RPCException, RPCClient
from core_modules.logger import get_logger
from core_modules.ticket_models import RegistrationTicket
from utils.mn_ordering import get_masternode_ordering
from wallet.art_registration_client import ArtRegistrationClient
from wallet.database import RegticketDB, Masternode, Artwork, SellticketDB
from wallet.settings import BURN_ADDRESS, get_thumbnail_dir


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

        self.__logger = get_logger('Wallet interface')

        self.pastelid = pastelid
        self.passphrase = passphrase

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
    async def image_registration_step_2(self, regticket_data: dict, image_data: bytes):

        # Create and populate ticket ()
        artreg = ArtRegistrationClient()
        # generate_regticket creates:
        #   fingerprints
        #   luby blocks (hashes and seeds)
        #   thumbnail
        #   hashes of images and thumbnail
        regticket = ArtRegistrationClient.generate_regticket(image_data, regticket_data)

        # Send regticket to MN0; Receive upload_code; Upload image; Receive worker's fee
        result = await artreg.send_regticket_and_image_to_mn0(
            image_data=image_data,
            regticket=regticket
        )

        return result

    async def image_registration_step_3(self, regticket_id):
        artreg = ArtRegistrationClient()

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

        # Send txid of burnt 10% to MN0, MN1 and MN2
        mn0, mn1, mn2 = get_masternode_ordering(regticket_db.blocknum)[:3]

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
                # raise Exception('Txid not found neither in mn1 nor in mn2 response!')
                return {'status': 'ERROR',
                        'msg': 'Txid not found neither in mn1 nor in mn2 response!, '
                               'Responses: MN0: {}, MN1: {}, MN2: {}'.format(
                                mn0_response, mn1_response, mn2_response)}
            return {
                'status': 'SUCCESS',
                'txid': txid,
                'fee': regticket_db.worker_fee,
                'blocknum': regticket_db.blocknum,
                'pastel_id': self.pastelid,
                'passphrase': self.passphrase
            }
        else:
            # some error happened, return details
            return {
                'status': 'ERROR',
                'msg': {
                    'mn_data': {
                        'mn0': {'status': 'SUCCESS' if mn0_response[1] else 'ERROR',
                                'msg': mn0_response[0]},
                        'mn1': {'status': 'SUCCESS' if mn1_response[1] else 'ERROR',
                                'msg': mn1_response[0]},
                        'mn2': {'status': 'SUCCESS' if mn2_response[1] else 'ERROR',
                                'msg': mn2_response[0]}
                    }
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

    async def get_artworks_data(self):
        reg_tickets_txids = get_blockchain_connection().list_tickets('act')  # list
        txid_list = set(map(lambda x: x['ticket']['reg_txid'], reg_tickets_txids))
        db_txid_list = set([a.reg_ticket_txid for a in Artwork.select()])
        # get act ticket txids which are in blockchain and not in db_txid_list
        reg_ticket_txid_to_fetch = txid_list - db_txid_list
        if len(reg_ticket_txid_to_fetch):
            client = Masternode.select()[0].get_rpc_client()
            # fetch missing data from the blockchain and write to DB
            for txid in reg_ticket_txid_to_fetch:
                try:
                    ticket = get_blockchain_connection().get_ticket(txid) # it's registration ticket here
                except JSONRPCException as e:
                    self.__logger.exception('Error obtain registration ticket txid: {}'.format(txid))
                    # to avoid processing invalid txid multiple times - write in to the DB with height=-1
                    Artwork.create(reg_ticket_txid=txid, blocknum=-1)
                    continue
                try:
                    act_ticket = get_blockchain_connection().find_ticket('act', txid)
                except JSONRPCException as e:
                    self.__logger.exception('Error obtain act ticket by key: {}'.format(txid))
                    # to avoid processing invalid txid multiple times - write in to the DB with height=-1
                    Artwork.create(reg_ticket_txid=txid, blocknum=-1)
                    continue

                regticket = RegistrationTicket(serialized_base64=ticket['ticket']['art_ticket'])
                artist_pastelid = list(ticket['ticket']['signatures']['artist'].keys())[0]

                # get thumbnail
                response = await client.rpc_download_thumbnail(regticket.thumbnailhash)
                thumbnail_data = b''
                if response['status'] == "SUCCESS":
                    thumbnail_data = response['image_data']
                elif response['status'] == "ERROR":
                    if 'masternodes' in response:
                        # try to fetch thumbnail from recommended masternodes
                        for pastelid in response['masternodes']:
                            try:
                                rpc_client = Masternode.select().get(Masternode.pastel_id == pastelid).get_rpc_client()
                                response = await rpc_client.rpc_download_thumbnail(regticket.thumbnailhash)
                                if response['status'] == "SUCCESS":
                                    thumbnail_data = response['image_data']
                                    break
                                elif response['status'] == "ERROR":
                                    continue
                            except Exception:
                                continue

                thumbnail_filename = '{}.png'.format(txid)
                thumbnail_path = os.path.join(get_thumbnail_dir(), thumbnail_filename)
                with open(thumbnail_path, 'wb') as f:
                    f.write(thumbnail_data)
                # store artwork data to DB
                Artwork.create(reg_ticket_txid=txid, act_ticket_txid=act_ticket['txid'],
                               artist_pastelid=artist_pastelid,
                               artwork_title=regticket.artwork_title, total_copies=regticket.total_copies,
                               artist_name=regticket.artist_name, artist_website=regticket.artist_website,
                               artist_written_statement=regticket.artist_written_statement,
                               artwork_series_name=regticket.artwork_series_name,
                               artwork_creation_video_youtube_url=regticket.artwork_creation_video_youtube_url,
                               artwork_keyword_set=regticket.artwork_keyword_set,
                               imagedata_hash=regticket.imagedata_hash,
                               blocknum=regticket.blocknum,
                               order_block_txid=regticket.order_block_txid
                               )
        result = []
        for artwork in Artwork.select().where(Artwork.blocknum > 0):
            sale_data = {
                'forSale': False,
                'price': -1
            }

            response = get_blockchain_connection().find_ticket('sell', artwork.act_ticket_txid)
            sell_ticket = SellticketDB.get_or_none(SellticketDB.act_ticket_txid == artwork.act_ticket_txid)
            if response == 'Key is not found':
                if sell_ticket == None:
                    pass
                else:
                    sale_data = {
                        'forSale': True,
                        'price': sell_ticket.price
                    }
            elif type(response) == list:
                resp_json = response[0]
                sale_data = {
                    'forSale': True,
                    'price': resp_json['ticket']['asked_price']
                }
            elif type(response) == str:
                resp_json = json.loads(response)
                sale_data = {
                    'forSale': True,
                    'price': resp_json['ticket']['asked_price']
                }
            result.append({
                'artistPastelId': artwork.artist_pastelid,
                'name': artwork.artwork_title,
                'numOfCopies': artwork.total_copies,
                'copyPrice': -1,
                'thumbnailPath': artwork.get_thumbnail_path(),
                'artistName': artwork.artist_name,
                'artistWebsite': artwork.artist_website,
                'artistWrittenStatement': artwork.artist_written_statement,
                'artworkSeriesName': artwork.artwork_series_name,
                'artworkCreationVideoYoutubeUrl': artwork.artwork_creation_video_youtube_url,
                'artworkKeywordSet': artwork.artwork_keyword_set,
                'imageHash': artwork.get_image_hash_digest(),
                'blocknum': artwork.blocknum,
                'orderBlockTxid': artwork.order_block_txid,
                'actTicketTxid': artwork.act_ticket_txid,
                'saleData': sale_data
            })
        return result

    async def register_sell_ticket(self, txid, price):
        act_txid = txid
        result = get_blockchain_connection().register_sell_ticket(act_txid, price)
        SellticketDB.create(pastelid=self.pastelid, price=price, act_ticket_txid=act_txid)
        return result
