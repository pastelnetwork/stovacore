import asyncio
import base64
import json
import random

from bitcoinrpc.authproxy import JSONRPCException
from peewee import DoesNotExist, IntegrityError

from core_modules.database import Masternode, Chunk, ChunkMnDistance, Regticket, ChunkMnRanked, MASTERNODE_DB, \
    ActivationTicket
from core_modules.logger import get_logger
from core_modules.chunkmanager import get_chunkmanager
from core_modules.ticket_models import RegistrationTicket
from core_modules.rpc_client import RPCException
from core_modules.settings import Settings
from core_modules.helpers import get_pynode_digest_int, chunkid_to_hex
from cnode_connection import get_blockchain_connection

tasks_logger = get_logger('Tasks')
chunk_storage_logger = get_logger('ChunkStorage')

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
        tasks_logger.warn('Got new Masternodes. Adding to the list')

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
    chunk_storage_logger.info('Calculating XOR distance for {} chunks...'.format(len(chunk_ids)))
    chunk_ids_str = [str(x) for x in chunk_ids]
    chunks_db = Chunk.select().where(Chunk.chunk_id.in_(chunk_ids_str))
    counter = 0
    for chunk in chunks_db:
        for mn in Masternode.get_active_nodes():
            # we store chunk.chunk_id as CharField, but essentially it's very long integer (more then 8 bytes,
            # doesn't fit in database INT type)
            xor_distance = calculate_xor_distance(mn.pastel_id, int(chunk.chunk_id))
            ChunkMnDistance.create(chunk=chunk, masternode=mn, distance=str(xor_distance))
            counter +=1
    chunk_storage_logger.info('..Caculated {} distances'.format(counter))


def index_new_chunks():
    """
    Select chunks which has not been indexed (XOR distance is not calculated) and calculate XOR distance for them.
    """
    chunk_qs = Chunk.select().where(Chunk.indexed == False)
    chunk_ids = [int(c.chunk_id) for c in chunk_qs]
    if len(chunk_ids):
        chunk_storage_logger.info('index_new_chunks found {} unprocessed chunks. Processing...'.format(len(chunk_ids)))
        calculate_xor_distances_for_chunks(chunk_ids)
        # update all processed chunks with `indexed` = True
        for chunk in chunk_qs:
            chunk.indexed = True
        Chunk.bulk_update(chunk_qs, fields=[Chunk.indexed])
        chunk_storage_logger.info('Updating Chunk.indexed flag for processed chunks in DB')
        # calculate chunk-mn-ranks as list of chunks was changed
        recalculate_mn_chunk_ranking_table()


def get_registration_ticket_object_from_data(ticket):
    return RegistrationTicket(serialized_base64=ticket['ticket']['art_ticket'])


def get_and_proccess_new_activation_tickets():
    """
    As as input we have list of new activation ticket.
    Outputs of this task are:
     - Store appropriate registration tickets in local DB, marking them confirmed
     - Store chunks from these registration tickets in local DB, marking them confirmed.
     (which will be used by another chunk-processing tasks).
    """
    # FIXME: use `height` param when it will be implemented on cNode
    act_tickets = get_blockchain_connection().list_tickets('act')  # list if dicts with actticket data
    act_tickets_txids = [ticket['txid'] for ticket in act_tickets]
    if act_tickets_txids is None:
        return

    for txid in filter(lambda x: len(x) == TXID_LENGTH, act_tickets_txids):
        if ActivationTicket.select().where(ActivationTicket.txid == txid).count() != 0:
            continue

        tasks_logger.info('New activation ticket found: {}'.format(txid))

        try:
            act_ticket = get_blockchain_connection().get_ticket(txid)
        except JSONRPCException as e:
            tasks_logger.exception('Exception while fetching actticket: {}'.format(str(e)))
            # to avoid processing invalid txid multiple times - write in to the DB with height=-1
            ActivationTicket.create(txid=txid, height=-1)
            continue
        # fetch regticket from activation ticket
        # store regticket in local DB if not exist
        # get list of chunk ids, add to local DB (Chunk table)
        regticket_data = get_blockchain_connection().get_ticket(act_ticket['ticket']['reg_txid'])
        regticket = get_registration_ticket_object_from_data(regticket_data)
        chunk_hashes = regticket.lubyhashes  # this is list of bytes objects

        # add thumbnail chunk
        try:
            tasks_logger.info('Creating Chunk record for thumbnail, hash {}'.format(regticket.thumbnailhash))
            chunk = Chunk.create_from_hash(chunkhash=regticket.thumbnailhash, artwork_hash=regticket.thumbnailhash)
        except IntegrityError:  # if Chunk with such chunkhash already exist
            tasks_logger.error('Error: thumbnail chunk already exists')
            chunk = Chunk.get_by_hash(chunkhash=regticket.thumbnailhash)
        chunk.confirmed = True
        chunk.save()

        chunks_created, chunks_updated = 0,0
        tasks_logger.info('Creating chunks record for artwork chunks...')
        for chunkhash in chunk_hashes:
            # if chunk exists - mark it as confirmed
            # else - create it. And mark as confirmed. More frequently we'll have no such chunk.
            try:
                chunk = Chunk.create_from_hash(chunkhash=chunkhash, artwork_hash=regticket.imagedata_hash)
                chunks_created += 1
            except IntegrityError:  # if Chunk with such chunkhash already exist
                chunk = Chunk.get_by_hash(chunkhash=chunkhash)
                chunks_updated += 1
            chunk.confirmed = True
            chunk.save()
        tasks_logger.info('...Complete! Created {}, updated {} chunks'.format(chunks_created, chunks_updated))

        # write processed act ticket to DB
        tasks_logger.info('Activation ticket processed, writing to the DB. Height: {}'.format(regticket_data['height']))
        ActivationTicket.create(txid=txid, height=act_ticket['height'])


def move_confirmed_chunks_to_persistant_storage():
    """
    Task which moves chunks from temp storage to persistent one.
     - Goes through chunks in temp storage,
     - fetch each chunk from DB, if it's confirmed - move to persistant storage.
    """
    for chunk_id in get_chunkmanager().index_temp_storage():
        tasks_logger.warn('Process chunk {}'.format(chunk_id))
        try:
            chunk_db = Chunk.get(chunk_id=chunk_id)
        except DoesNotExist:
            tasks_logger.exception('Chunk with id {} does not exist in DB but exist in local storage'.format(chunk_id))
            get_chunkmanager().rm_from_temp_storage(chunk_id)
            continue
        if chunk_db.confirmed:
            # move to persistant storge
            tasks_logger.warn('Move chunk to persistant storage')
            get_chunkmanager().move_to_persistant_storage(chunk_id)


def recalculate_mn_chunk_ranking_table():
    """
    This method recalculates all ranks of masternodes for each chunk. Is tend to be slow (if the number of chunks
    and masternode will be big), so it needs to be called only when new masternode is added.
    There is a sense to limit frequence of calls (say, no more then once a minute or so).
    """
    # calculate each masternode rank for each chunk
    tasks_logger.info('ChunkMnRanked table has {} record. Recalculating...'.format(ChunkMnRanked.select().count()))
    subquery = '''
    select chunk_id, masternode_id, row_number() 
    over (partition by chunk_id order by distance asc) as r 
    from chunkmndistance
    '''

    # leave only top `Settings.REPLICATION_FACTOR` masternodes (which are considered as chunk owners).
    sql = '''select chunk_id, masternode_id, r from ({}) as t where t.r<={}'''.format(
        subquery,
        Settings.REPLICATION_FACTOR
    )

    # delete old rows
    ChunkMnRanked.delete().execute()

    # insert (chunk, masternode, rank) for all chunk-owners in a separate table for convinience
    insert_sql = '''insert into chunkmnranked (chunk_id, masternode_id, rank) {}'''.format(sql)
    MASTERNODE_DB.execute_sql(insert_sql)
    tasks_logger.info('...Done. Now here are {} records'.format(ChunkMnRanked.select().count()))


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
        (ChunkMnRanked.masternode_id == current_mn_id) & (Chunk.stored == False) & (Chunk.attempts_to_load < 1000))
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
            tasks_logger.exception('Exception in process tmp storage task: {}'.format(ex))


async def process_new_tickets_task():
    tasks_logger.info('Process new tickets task started..')
    while True:
        await asyncio.sleep(1)
        try:
            get_and_proccess_new_activation_tickets()
        except Exception as ex:
            tasks_logger.exception('Exception in process new tickets task: {}'.format(ex))
            tasks_logger.info('Process new tickets task finished')


async def masternodes_refresh_task():
    while True:
        await asyncio.sleep(1)
        try:
            refresh_masternode_list()
        except Exception as ex:
            tasks_logger.exception('Exception in masternode refresh task: {}'.format(ex))


async def index_new_chunks_task():
    chunk_storage_logger.info('Index new chunks task started...')
    while True:
        await asyncio.sleep(1)
        try:
            index_new_chunks()
        except Exception as ex:
            tasks_logger.exception('Exception in Index new chunks task: {}'.format(ex))


async def fetch_single_chunk_via_rpc(chunkid):
    for masternode in get_chunk_owners(chunkid):
        if masternode.pastel_id == get_blockchain_connection().pastelid:
            # don't attempt to connect ourselves
            continue

        mn = masternode.get_rpc_client()

        try:
            data = await mn.send_rpc_fetchchunk(chunkid)
        except RPCException as exc:
            tasks_logger.exception("FETCHCHUNK RPC FAILED for node %s with exception %s" % (mn.server_ip, exc))
            continue
        except Exception as ex:
            tasks_logger.exception("FETCHCHUNK RPC FAILED for node %s with exception %s" % (mn.server_ip, ex))
            continue

        if data is None:
            tasks_logger.debug("MN %s returned None for fetchchunk %s" % (mn.server_ip, chunkid))
            # chunk was not found
            continue

        # if chunk is received:
        # verify that digest matches
        digest = get_pynode_digest_int(data)
        if chunkid != str(digest):
            tasks_logger.info("MN %s returned bad chunk for fetchchunk %s, mismatched digest: %s" % (
                mn.server_ip, chunkid, digest))
            continue
        return data
    # nobody has this chunk
    tasks_logger.error("Unable to fetch chunk %s" %
                     chunkid_to_hex(int(chunkid)))

FIBONACHI_ROW = {0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987}


async def fetch_chunk_and_store_it(chunkid):
    chunk = Chunk.get(Chunk.chunk_id == chunkid)
    if chunk.attempts_to_load not in FIBONACHI_ROW:
        chunk.attempts_to_load += 1
        chunk.save()
        return False

    data = await fetch_single_chunk_via_rpc(chunkid)
    if data:
        # add chunk to persistant storage and update DB info (`stored` flag) to True
        get_chunkmanager().store_chunk_in_storage(int(chunkid), data)
        chunk.stored = True
        chunk.attempts_to_load += 1
        chunk.save()
        return True
    else:
        chunk.attempts_to_load += 1
        chunk.save()
        return False


async def chunk_fetcher_task_body(pastel_id=None):
    missing_chunk_ids = get_missing_chunk_ids(pastel_id)
    if len(missing_chunk_ids):
        tasks_logger.info('Chunk fetcher found {} chunks to fetch...'.format(len(missing_chunk_ids)))
    else:
        return
    missing_chunk_ids_to_process = missing_chunk_ids[:Settings.CHUNK_FETCH_PARALLELISM]
    tasks = []
    for missing_chunk in missing_chunk_ids_to_process:
        tasks.append(fetch_chunk_and_store_it(missing_chunk))

    results = await asyncio.gather(*tasks)
    tasks_logger.info('...Fetched {} chunks'.format(results.count(True)))


async def chunk_fetcher_task():
    tasks_logger.info("Starting chunk fetcher...")
    while True:
        try:
            await chunk_fetcher_task_body()
        except Exception as ex:
            tasks_logger.exception('Exception in chunk fetcher task: {}'.format(ex))
        await asyncio.sleep(10)
