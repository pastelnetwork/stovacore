import asyncio

from peewee import DoesNotExist, IntegrityError, fn

from core_modules.database import Masternode, Chunk, ChunkMnDistance, Regticket, ChunkMnRanked, MASTERNODE_DB
from core_modules.logger import initlogging
from core_modules.artregistry import ArtRegistry
from core_modules.autotrader import AutoTrader
from core_modules.blockchain import NotEnoughConfirmations
from core_modules.chainwrapper import ChainWrapper
from core_modules.chunkmanager import ChunkManager, get_chunkmanager
from core_modules.chunkmanager_modules.chunkmanager_rpc import ChunkManagerRPC
from core_modules.chunkmanager_modules.aliasmanager import AliasManager
from core_modules.ticket_models import FinalActivationTicket, FinalTransferTicket, FinalTradeTicket, RegistrationTicket
from core_modules.http_rpc import RPCException, RPCServer
from pynode.masternode_communication import MasternodeManager
from core_modules.masternode_ticketing import ArtRegistrationServer
from core_modules.settings import NetWorkSettings
from core_modules.helpers import get_pynode_digest_int, bytes_to_chunkid, chunkid_to_hex
from cnode_connection import get_blockchain_connection

mnl_logger = initlogging('', __name__)


def update_masternode_list():
    """
    Fetch current masternode list from cNode (by calling `masternode list extra`) and
    update database Masternode table accordingly.
    Return 2 sets of MN pastelIDs - added and removed,
    """
    masternode_list = get_blockchain_connection().masternode_list()

    # parse new list
    fresh_mn_list = {}
    for k in masternode_list:
        node = masternode_list[k]
        # generate dict of {pastelid: <ip:port>}
        if len(node['extKey']) > 20 and len(node['extAddress']) > 4:
            fresh_mn_list[node['extKey']] = node['extAddress']

    existing_mn_pastelids = set([mn.pastel_id for mn in Masternode.select()])
    fresh_mn_pastelids = set(fresh_mn_list.keys())
    added_pastelids = fresh_mn_pastelids - existing_mn_pastelids
    removed_pastelids = existing_mn_pastelids - fresh_mn_pastelids
    if len(removed_pastelids):
        Masternode.delete().where(Masternode.pastel_id.in_(removed_pastelids)).execute()

    if len(added_pastelids):
        data_for_insert = [{'pastel_id': pastelid, 'ext_address': fresh_mn_list[pastelid]} for pastelid in
                           added_pastelids]
        Masternode.insert(data_for_insert).execute()
    return added_pastelids, removed_pastelids


def refresh_masternode_list():
    """
    Update MN list in database, initiate distance calculation for added masternodes
    """
    added, removed = update_masternode_list()
    calculate_xor_distances_for_masternodes(added)


def calculate_xor_distance(pastelid, chunkid):
    """
    This method is single point of calculating XOR distance between pastelid and chunkid.
    PastelID is initially string. There is a number of ways to convert string to some integer value
    (depending on the input string), but it's important to select one way and keep it.
    `chunkid` is expected to be integer.
    """
    # there is
    node_digest = get_pynode_digest_int(pastelid.encode())
    xor_distance = node_digest ^ chunkid
    return xor_distance


def calculate_xor_distances_for_masternodes(pastelids):
    """
    `pastelids` - list of pastelids of masternodes. PastelID is a string.
    """
    mns_db = Masternode.select().where(Masternode.pastel_id.in_(pastelids))
    for mn in mns_db:
        for chunk in Chunk.select():
            # we store chunk.chunk_id as CharField, but essentially it's very long integer (more then 8 bytes,
            # doesn't fit in database INT type)
            xor_distance = calculate_xor_distance(mn.pastel_id, int(chunk.chunk_id))
            ChunkMnDistance.create(chunk=chunk, masternode=mn, distance=str(xor_distance))


def calculate_xor_distances_for_chunks(chunk_ids):
    """
    `chunk_ids` - list of chunks ids. Chunk ID is a very long integer.
    """
    chunk_ids_str = [str(x) for x in chunk_ids]
    chunks_db = Chunk.select().where(Chunk.chunk_id.in_(chunk_ids_str))
    for chunk in chunks_db:
        for mn in Masternode.select():
            # we store chunk.chunk_id as CharField, but essentially it's very long integer (more then 8 bytes,
            # doesn't fit in database INT type)
            xor_distance = calculate_xor_distance(mn.pastel_id, int(chunk.chunk_id))
            ChunkMnDistance.create(chunk=chunk, masternode=mn, distance=str(xor_distance))


def index_new_chunks():
    """
    Select chunks which has not been indexed (XOR distance is not calculated) and calculate XOR distance for them.
    """
    chunk_qs = Chunk.select().where(Chunk.indexed == False)
    chunk_ids = [int(c.chunk_id) for c in chunk_qs]
    if len(chunk_ids):
        calculate_xor_distances_for_chunks(chunk_ids)
        # update all processed chunks with `indexed` = True
        for chunk in chunk_qs:
            chunk.indexed = True
        Chunk.bulk_update(chunk_qs, fields=[Chunk.indexed])


def get_registration_ticket_from_act_ticket(act_ticket):
    # TODO: implement
    return RegistrationTicket()


def get_and_proccess_new_activation_tickets():
    """
    As as input we have list of new activation ticket.
    Outputs of this task are:
     - Store appropriate registration tickets in local DB, marking them confirmed
     - Store chunks from these registration tickets in local DB, marking them confirmed.
     (which will be used by another chunk-processing tasks).
    """
    # get tickets
    # FIXME: make sure that we get only new, unprocessed tickets here
    # tickets = get_blockchain_connection().list_tickets('conf')
    # TODO: Output of this task: current masternode get new chunk IDs into its local DB.
    # TODO: Then it calculates distances, fetches required chunks (or moves them to the persistent storage).
    tickets = [
        {
            'txid': '',
            'pastelid': '',
            'regticket_txid': ''
        }
    ]
    for ticket in tickets:
        # fetch regticket from activation ticket
        # store regticket in local DB if not exist
        # get list of chunk ids, add to local DB (Chunk table)
        regticket = get_registration_ticket_from_act_ticket(ticket)
        try:
            regticket_db = Regticket.get(image_hash=regticket.imagedata_hash)
            regticket_db.confirmed = True
            regticket_db.save()
        except DoesNotExist:
            regticket_db = Regticket.create(
                artist_pk=regticket.author,
                image_hash=regticket.imagedata_hash,
                regticket=regticket.serialize(),
                confirmed=True
            )
        chunk_hashes = regticket.lubyhashes  # this is list of bytes objects
        for chunkhash in chunk_hashes:
            # FIXME: it can be speed up with bulk_update and bulk_create
            # if chunk exists - mark it as confirmed
            # else - create it. And mark as confirmed. More frequently we'll have no such chunk.
            try:
                chunk = Chunk.create_from_hash(chunkhash=chunkhash, artwork_hash=regticket.imagedata_hash)
            except IntegrityError:  # if Chunk with such chunkhash already exist
                chunk = Chunk.get_by_hash(chunkhash=chunkhash)
            chunk.confirmed = True
            chunk.save()


def move_confirmed_chunks_to_persistant_storage():
    """
    Task which moves chunks from temp storage to persistent one.
     - Goes through chunks in temp storage,
     - fetch each chunk from DB, if it's confirmed - move to persistant storage.
    """

    for chunk_id in get_chunkmanager().index_temp_storage:
        chunk_db = Chunk.get(chunk_id=chunk_id)
        if chunk_db.confirmed:
            # move to persistant storge
            get_chunkmanager().move_to_persistant_storage(chunk_id)


def recalculate_mn_chunk_ranking_table():
    """
    This method recalculates all ranks of masternodes for each chunk. Is tend to be slow (if the number of chunks
    and masternode will be big), so it needs to be called only when new masternode is added.
    There is a sense to limit frequence of calls (say, no more then once a minute or so).
    """
    # FIXME: it would be clearer and more readable to implement all this SQL with Peewee ORM.
    # ChunkMnDistance.select(
    #     ChunkMnDistance.chunk,
    #     ChunkMnDistance.masternode,
    #     fn.ROW_NUMBER().over(partition_by=[ChunkMnDistance.chunk], order_by=[ChunkMnDistance.distance]).alias('r'))

    # calculate each masternode rank for each chunk
    subquery = '''
    select chunk_id, masternode_id, row_number() 
    over (partition by chunk_id order by distance asc) as r 
    from chunkmndistance
    '''

    # leave only top `NetWorkSettings.REPLICATION_FACTOR` masternodes (which are considered as chunk owners).
    sql = '''select chunk_id, masternode_id, r from ({}) as t where t.r<={}'''.format(
        subquery,
        NetWorkSettings.REPLICATION_FACTOR
    )

    # delete old rows
    ChunkMnRanked.delete().execute()

    # insert (chunk, masternode, rank) for all chunk-owners in a separate table for convinience
    insert_sql = '''insert into chunkmnranked (chunk_id, masternode_id, rank) {}'''.format(sql)
    MASTERNODE_DB.execute_sql(insert_sql)


def get_owned_chunks():
    """
    Return list of database chunk records we should store.
    """
    current_mn_id = Masternode.get(pastel_id=get_blockchain_connection().pastelid).id
    chunks_ranked_qs = ChunkMnRanked.select().where(ChunkMnRanked.masternode_id==current_mn_id)
    return [c.chunk for c in chunks_ranked_qs]


def get_chunk_owners(chunk_id):
    """
    Return list of masternodes who's expected to store a given chunk
    """
    db_chunk = Chunk.get(chunk_id=str(chunk_id))
    return [c.masternode for c in ChunkMnRanked.select().where(ChunkMnRanked.chunk==db_chunk)]


def download_missing_chunks():
    # TODO: task which get list of chunks we should own, and download missing
    #   - calculate list of chunks we should own. it makes sense to cache calculation. (caching is easy, but proper
    #   cache invalidation is not very..)
    #   - calculate all owners for a given chunk (select masternode_id from ChunkMnDistance where chunk=<chunk>
    #   order by distance asc limit 10;
    pass


async def proccess_tmp_storage():
    while True:
        # it should not be called very often. New result will be if there are new act tickets parsed
        await asyncio.sleep(5)
        move_confirmed_chunks_to_persistant_storage()


async def process_new_tickets_task():
    while True:
        await asyncio.sleep(1)
        get_and_proccess_new_activation_tickets()


async def masternodes_refresh_task():
    while True:
        await asyncio.sleep(1)
        refresh_masternode_list()


async def index_new_chunks_task():
    while True:
        await asyncio.sleep(1)
        index_new_chunks()


class MasterNodeLogic:
    def __init__(self):

        self.__logger = initlogging('', __name__)

        # the art registry
        self.__artregistry = ArtRegistry()

        # set up ChainWrapper
        self.__chainwrapper = ChainWrapper(self.__artregistry)

        # the automatic trader
        self.__autotrader = AutoTrader(self.__artregistry)

        # masternode manager
        self.__mn_manager = MasternodeManager()

        # alias manager
        self.__aliasmanager = AliasManager()

        # chunk manager
        self.__chunkmanager = ChunkManager(self.__aliasmanager)

        self.__chunkmanager_rpc = ChunkManagerRPC(self.__chunkmanager, self.__mn_manager,
                                                  self.__aliasmanager)

        # art registration server
        self.__artregistrationserver = ArtRegistrationServer(self.__chainwrapper,
                                                             self.__chunkmanager)

        # start rpc server
        self.__rpcserver = RPCServer()

        self.__rpcserver.add_callback("SPOTCHECK_REQ", "SPOTCHECK_RESP",
                                      self.__chunkmanager_rpc.receive_rpc_spotcheck)
        self.__rpcserver.add_callback("FETCHCHUNK_REQ", "FETCHCHUNK_RESP",
                                      self.__chunkmanager_rpc.receive_rpc_fetchchunk)

        self.__rpcserver.add_callback("IMAGEDOWNLOAD_REQ", "IMAGEDOWNLOAD_RESP",
                                      self.__chunkmanager_rpc.receive_rpc_download_image)

        self.__artregistrationserver.register_rpcs(self.__rpcserver)

        # we like to enable/disable this from masternodedaemon
        self.issue_random_tests_forever = self.__chunkmanager_rpc.issue_random_tests_forever

    async def run_ticket_parser(self):
        # sleep to start fast
        await asyncio.sleep(0)

        current_block = 0
        while True:
            try:
                # get the block count to be used later
                blockcount = get_blockchain_connection().getblockcount()

                # try to get block - will raise NotEnoughConfirmations if block is not mature
                # we do this so that it's guaranteed that we don't update artregistry with a bad block
                get_blockchain_connection().get_txids_for_block(current_block,
                                                                confirmations=NetWorkSettings.REQUIRED_CONFIRMATIONS)

                # update current block height in artregistry - this purges old tickets / matches
                self.__artregistry.update_current_block_height(current_block)

                # notify objects of the tickets discovered
                for txid, transtype, data in self.__chainwrapper.get_transactions_for_block(current_block):
                    # tickets receveid by get_transactions_for_block are validated

                    # get the currently listened-for addresses:
                    # we do this here as tickets in a block might add new stuff for the same block
                    listen_addresses, listen_utxos = self.__artregistry.get_listen_addresses_and_utxos()

                    if transtype == "ticket":
                        ticket = data

                        # only parse FinalActivationTickets for now
                        if type(ticket) == FinalActivationTicket:
                            # fetch corresponding finalregticket
                            final_regticket = self.__chainwrapper.retrieve_ticket(
                                ticket.ticket.registration_ticket_txid)

                            # get the actual regticket
                            regticket = final_regticket.ticket

                            # get the chunkids that we need to store
                            chunks = []
                            for chunkid_bytes in [regticket.thumbnailhash] + regticket.lubyhashes:
                                chunkid = bytes_to_chunkid(chunkid_bytes)
                                chunks.append(chunkid)

                            # add this chunkid to chunkmanager
                            self.__chunkmanager.add_new_chunks(chunks)

                            # add ticket to artregistry
                            self.__artregistry.add_artwork(txid, ticket, regticket)
                        elif type(ticket) == FinalTransferTicket:
                            # get the transfer ticket
                            transfer_ticket = ticket.ticket
                            transfer_ticket.validate(self.__chainwrapper, self.__artregistry)

                            # add ticket to artregistry
                            self.__artregistry.add_transfer_ticket(txid, transfer_ticket)
                        elif type(ticket) == FinalTradeTicket:
                            # get the transfer ticket
                            trade_ticket = ticket.ticket
                            trade_ticket.validate(self.__chainwrapper, self.__artregistry)

                            # add ticket to artregistry
                            self.__artregistry.add_trade_ticket(txid, trade_ticket)
                    else:
                        transaction = data

                        # check on the transaction
                        # NOTE: do vout first, as we don't want to invalidate a ticket when payment
                        #       is made, due to the colletral being used as payment

                        # for addresses we plan to receive payments to
                        for vout in transaction["vout"]:
                            if len(vout["scriptPubKey"]["addresses"]) > 1:
                                continue

                            # valid transaction received, notify artregistry
                            value = vout["value"]
                            address = vout["scriptPubKey"]["addresses"][0]
                            if address in listen_addresses:
                                self.__artregistry.process_watched_vout(address, value)

                        # Do vin second, if collateral has been used as legit payment we consummated
                        # the train above. If not, the ticket needs invalidation
                        for vin in transaction["vin"]:
                            if vin.get("txid") is not None:
                                if vin["txid"] in listen_utxos:
                                    self.__artregistry.process_watched_vin(vin["txid"])

                # new tickets are in, call automatic trader
                if current_block < blockcount:
                    # only print a message every 2%
                    if blockcount >= 20:
                        if current_block % int(blockcount / 50) == 0:
                            self.__logger.debug("Parsing historic block %s / %s (%.2f%%)" % (
                                current_block, blockcount, current_block / blockcount * 100))
                    else:
                        pass
                else:
                    if not self.__autotrader.enabled():
                        self.__logger.debug("Done parsing history, enabling autottrader")
                        self.__autotrader.enable()

                # update autotrade - this is a NOP until enabled() is called
                self.__autotrader.consummate_trades()
            except NotEnoughConfirmations:
                # this block hasn't got enough confirmations yet
                await asyncio.sleep(1)
            else:
                # successfully parsed this block
                current_block += 1
                await asyncio.sleep(0)

    async def run_heartbeat_forever(self):
        while True:
            await asyncio.sleep(1)
            self.__chunkmanager.dump_internal_stats("HEARTBEAT")

    async def run_ping_test_forever(self):
        while True:
            await asyncio.sleep(1)

            mn = self.__mn_manager.get_random()
            if mn is None:
                continue

            data = b'PING'

            try:
                response_data = await mn.send_rpc_ping(data)
            except RPCException as exc:
                self.__logger.info("PING RPC FAILED for node %s with exception %s" % (mn, exc))
            else:
                if response_data != data:
                    self.__logger.warning("PING FAILED for node %s (%s != %s)" % (mn, data, response_data))
                else:
                    self.__logger.debug("PING SUCCESS for node %s for chunk: %s" % (mn, data))

                # TODO: track successes/errors

    async def run_chunk_fetcher_forever(self):
        async def fetch_single_chunk_via_rpc(chunkid):
            # we need to fetch it
            found = False
            for owner in self.__aliasmanager.find_other_owners_for_chunk(chunkid):
                mn = self.__mn_manager.get(owner)

                try:
                    data = await mn.send_rpc_fetchchunk(chunkid)
                except RPCException as exc:
                    self.__logger.info("FETCHCHUNK RPC FAILED for node %s with exception %s" % (owner, exc))
                    continue

                if data is None:
                    self.__logger.info("MN %s returned None for fetchchunk %s" % (owner, chunkid))
                    # chunk was not found
                    continue

                # verify that digest matches
                digest = get_pynode_digest_int(data)
                if chunkid != digest:
                    self.__logger.info("MN %s returned bad chunk for fetchchunk %s, mismatched digest: %s" % (
                        owner, chunkid, digest))
                    continue

                # we have the chunk, store it!
                self.__chunkmanager.store_missing_chunk(chunkid, data)
                break

            # nobody has this chunk
            if not found:
                # TODO: fall back to reconstruct it from luby blocks
                self.__logger.error("Unable to fetch chunk %s, luby reconstruction is not yet implemented!" %
                                    chunkid_to_hex(chunkid))
                self.__chunkmanager.failed_to_fetch_chunk(chunkid)

        while True:
            await asyncio.sleep(0)

            missing_chunks = self.__chunkmanager.get_random_missing_chunks(NetWorkSettings.CHUNK_FETCH_PARALLELISM)

            if len(missing_chunks) == 0:
                # nothing to do, sleep a little
                await asyncio.sleep(1)
                continue

            tasks = []
            for missing_chunk in missing_chunks:
                tasks.append(fetch_single_chunk_via_rpc(missing_chunk))

            await asyncio.gather(*tasks)
            await asyncio.sleep(1)

    async def run_rpc_server(self):
        await self.__rpcserver.run_server()

    async def stop_rpc_server(self):
        await self.__rpcserver.stop_server()
