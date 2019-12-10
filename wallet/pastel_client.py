import asyncio
import uuid

from bitcoinrpc.authproxy import JSONRPCException

from cnode_connection import get_blockchain_connection
from core_modules.artregistry import ArtRegistry
from core_modules.chainwrapper import ChainWrapper
from core_modules.rpc_client import RPCException, RPCClient
from core_modules.logger import initlogging
from utils.mn_ordering import get_masternode_ordering
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
                raise Exception('Txid not found neither in mn1 nor in mn2 response!')
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
