import asyncio
import base64
import json
import random

from bitcoinrpc.authproxy import JSONRPCException
from peewee import DoesNotExist, IntegrityError

from core_modules.database import Masternode, Chunk, ChunkMnDistance, Regticket, ChunkMnRanked, MASTERNODE_DB, \
    ActivationTicket
from core_modules.logger import initlogging
from core_modules.chunkmanager import get_chunkmanager
from core_modules.ticket_models import RegistrationTicket
from core_modules.rpc_client import RPCException
from core_modules.settings import NetWorkSettings
from core_modules.helpers import get_pynode_digest_int, chunkid_to_hex
from cnode_connection import get_blockchain_connection

mnl_logger = initlogging('', __name__)

TXID_LENGTH = 64


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

    existing_mn_pastelids = set([mn.pastel_id for mn in Masternode.get_active_nodes()])
    fresh_mn_pastelids = set(fresh_mn_list.keys())
    added_pastelids = fresh_mn_pastelids - existing_mn_pastelids
    removed_pastelids = existing_mn_pastelids - fresh_mn_pastelids

    # FIXME: uncomment this if cNode will not return empty keys.
    # cNode returns empty extKey for random masternode, but it does not mean that this MNs should be deleted..
    # maybe need to delete MN only if it has not responses several times for fetch chunk request
    # if len(removed_pastelids):
    #     Masternode.delete().where(Masternode.pastel_id.in_(removed_pastelids)).execute()

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
    if added:
        calculate_xor_distances_for_masternodes(added)
        recalculate_mn_chunk_ranking_table()


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
    mns_db = Masternode.get_active_nodes().where(Masternode.pastel_id.in_(pastelids))
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
        for mn in Masternode.get_active_nodes():
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

        # calculate chunk-mn-ranks as list of chunks was changed
        recalculate_mn_chunk_ranking_table()


def get_registration_ticket_from_act_ticket(ticket):
    # regticket_txid = act_ticket['ticket']['reg_txid']
    # ticket = get_blockchain_connection().get_ticket(regticket_txid)
    # ticket['ticket']['art_ticket']  - it's cnode package
    return RegistrationTicket(serialized_base64=ticket['ticket']['art_ticket'])


def get_and_proccess_new_activation_tickets():
    """
    As as input we have list of new activation ticket.
    Outputs of this task are:
     - Store appropriate registration tickets in local DB, marking them confirmed
     - Store chunks from these registration tickets in local DB, marking them confirmed.
     (which will be used by another chunk-processing tasks).
    """
    # get tickets
    # FIXME: use `height` param when it will be implemented on cNode
    act_tickets_txids = get_blockchain_connection().list_tickets('act')  # list

    for txid in filter(lambda x: len(x) == TXID_LENGTH, act_tickets_txids):
        if ActivationTicket.select().where(ActivationTicket.txid == txid).count() != 0:
            continue
        try:
            ticket = json.loads(get_blockchain_connection().get_ticket(txid))  # it's registration ticket here
        except JSONRPCException as e:
            mnl_logger.error('Exception while fetching actticket: {}'.format(str(e)))
            # to avoid processing invalid txid multiple times - write in to the DB with height=-1
            ActivationTicket.create(txid=txid, height=-1)
            continue
        # fetch regticket from activation ticket
        # store regticket in local DB if not exist
        # get list of chunk ids, add to local DB (Chunk table)
        regticket = get_registration_ticket_from_act_ticket(ticket)
        chunk_hashes = regticket.lubyhashes  # this is list of bytes objects

        # add thumbnail chunk
        try:
            chunk = Chunk.create_from_hash(chunkhash=regticket.thumbnailhash, artwork_hash=regticket.thumbnailhash)
        except IntegrityError:  # if Chunk with such chunkhash already exist
            chunk = Chunk.get_by_hash(chunkhash=regticket.thumbnailhash)
        chunk.confirmed = True
        chunk.save()

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

        # write processed act ticket to DB
        ActivationTicket.create(txid=txid, height=ticket['height'])


def move_confirmed_chunks_to_persistant_storage():
    """
    Task which moves chunks from temp storage to persistent one.
     - Goes through chunks in temp storage,
     - fetch each chunk from DB, if it's confirmed - move to persistant storage.
    """
    for chunk_id in get_chunkmanager().index_temp_storage():
        mnl_logger.warn('Process chunk {}'.format(chunk_id))
        try:
            chunk_db = Chunk.get(chunk_id=chunk_id)
        except DoesNotExist:
            mnl_logger.warn('Chunk with id {} does not exist in DB but exist in local storage'.format(chunk_id))
            get_chunkmanager().rm_from_temp_storage(chunk_id)
            continue
        if chunk_db.confirmed:
            # move to persistant storge
            mnl_logger.warn('Move chunk to persistant storage')
            get_chunkmanager().move_to_persistant_storage(chunk_id)


def recalculate_mn_chunk_ranking_table():
    """
    This method recalculates all ranks of masternodes for each chunk. Is tend to be slow (if the number of chunks
    and masternode will be big), so it needs to be called only when new masternode is added.
    There is a sense to limit frequence of calls (say, no more then once a minute or so).
    """
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
    mnl_logger.info('query: {}'.format(insert_sql))
    MASTERNODE_DB.execute_sql(insert_sql)


def get_owned_chunks():
    """
    Return list of database chunk records we should store.
    """
    current_mn_id = Masternode.get(pastel_id=get_blockchain_connection().pastelid).id
    chunks_ranked_qs = ChunkMnRanked.select().where(ChunkMnRanked.masternode_id == current_mn_id)
    return [c.chunk for c in chunks_ranked_qs]


def get_missing_chunk_ids(pastel_id=None):
    """
    :param pastel_id: str
    :return: list of str chunkd ids (big integer numbers wrapper to string as they're stored in DB
    """
    if not pastel_id:
        pastel_id = get_blockchain_connection().pastelid
    # return chunks that we're owner of but don't have it in the storage
    try:
        current_mn_id = Masternode.get(pastel_id=pastel_id).id
    except DoesNotExist:
        return []
    chunks_ranked_qs = ChunkMnRanked.select().join(Chunk).where(
        (ChunkMnRanked.masternode_id == current_mn_id) & (Chunk.stored == False))
    return [c.chunk.chunk_id for c in chunks_ranked_qs]


def get_chunk_owners(chunk_id):
    """
    Return list of masternodes database objects who's expected to store a given chunk
    """
    db_chunk = Chunk.get(chunk_id=str(chunk_id))
    return [c.masternode for c in ChunkMnRanked.select().where(ChunkMnRanked.chunk == db_chunk)]


async def proccess_tmp_storage():
    while True:
        # it should not be called very often. New result will be if there are new act tickets parsed
        await asyncio.sleep(5)
        try:
            move_confirmed_chunks_to_persistant_storage()
        except Exception as ex:
            mnl_logger.error('Exception in process tmp storage task: {}'.format(ex))


async def process_new_tickets_task():
    while True:
        await asyncio.sleep(1)
        try:
            get_and_proccess_new_activation_tickets()
        except Exception as ex:
            mnl_logger.error('Exception in process new tickets task: {}'.format(ex))


async def masternodes_refresh_task():
    while True:
        await asyncio.sleep(1)
        try:
            refresh_masternode_list()
        except Exception as ex:
            mnl_logger.error('Exception in masternode refresh task: {}'.format(ex))


async def index_new_chunks_task():
    while True:
        await asyncio.sleep(1)
        try:
            index_new_chunks()
        except Exception as ex:
            mnl_logger.error('Exception in Index new chunks task: {}'.format(ex))


async def fetch_single_chunk_via_rpc(chunkid):
    for masternode in get_chunk_owners(chunkid):
        if masternode.pastel_id == get_blockchain_connection().pastelid:
            # don't attempt to connect ourselves
            continue

        mn = masternode.get_rpc_client()

        try:
            data = await mn.send_rpc_fetchchunk(chunkid)
        except RPCException as exc:
            mnl_logger.info("FETCHCHUNK RPC FAILED for node %s with exception %s" % (mn.server_ip, exc))
            continue

        if data is None:
            mnl_logger.info("MN %s returned None for fetchchunk %s" % (mn.server_ip, chunkid))
            # chunk was not found
            continue

        # if chunk is received:
        # verify that digest matches
        digest = get_pynode_digest_int(data)
        if chunkid != str(digest):
            mnl_logger.info("MN %s returned bad chunk for fetchchunk %s, mismatched digest: %s" % (
                mn.server_ip, chunkid, digest))
            continue
        return data
    # nobody has this chunk
    mnl_logger.error("Unable to fetch chunk %s" %
                     chunkid_to_hex(int(chunkid)))


async def fetch_chunk_and_store_it(chunkid):
    data = await fetch_single_chunk_via_rpc(chunkid)
    if data:
        # add chunk to persistant storage and update DB info (`stored` flag) to True
        get_chunkmanager().store_chunk_in_storage(int(chunkid), data)
        Chunk.update(stored=True).where(Chunk.chunk_id == chunkid).execute()


async def chunk_fetcher_task_body(pastel_id=None):
    missing_chunks = get_missing_chunk_ids(pastel_id)[:NetWorkSettings.CHUNK_FETCH_PARALLELISM]
    tasks = []
    for missing_chunk in missing_chunks:
        tasks.append(fetch_chunk_and_store_it(missing_chunk))

    await asyncio.gather(*tasks)


async def chunk_fetcher_task():
    while True:
        try:
            await chunk_fetcher_task_body()
        except Exception as ex:
            mnl_logger.error('Exception in chunk fetcher task: {}'.format(ex))
        await asyncio.sleep(1)


async def run_ping_test_forever(self):
    while True:
        await asyncio.sleep(1)

        Masternode.get_active_nodes()
        mn = random.sample(Masternode.get_active_nodes())
        if mn is None:
            continue

        data = b'PING'

        try:
            response_data = await mn.send_rpc_ping(data)
        except RPCException as exc:
            mnl_logger.info("PING RPC FAILED for node %s with exception %s" % (mn, exc))
        else:
            if response_data != data:
                mnl_logger.warning("PING FAILED for node %s (%s != %s)" % (mn, data, response_data))
            else:
                 mnl_logger.debug("PING SUCCESS for node %s for chunk: %s" % (mn, data))
