from core_modules.blackbox_modules import luby
from core_modules.chunkmanager import get_chunkmanager
from core_modules.database import Chunk, ChunkMnRanked, Masternode
from core_modules.helpers import hex_to_chunkid
from core_modules.logger import initlogging

rpc_handler_logger = initlogging('RPC Handler', __name__)


def receive_rpc_fetchchunk(data, **kwargs):
    if not isinstance(data, dict):
        raise TypeError("Data must be a dict!")

    if set(data.keys()) != {"chunkid"}:
        raise ValueError("Invalid arguments for spotcheck: %s" % (data.keys()))

    if not isinstance(data["chunkid"], str):
        raise TypeError("Invalid type for key chunkid in spotcheck")

    chunkid = hex_to_chunkid(data["chunkid"])  # here chunkid is long integer number

    # fetch chunk from DB, check if we store it
    chunk = Chunk.get(chunk_id=str(chunkid))  # if we dont have chunk - exception will be raised and returned by RPC
    if not chunk.stored:
        # raise RPCException('Given chunk is not stored')
        return {"chunk": None}
    chunk_data = get_chunkmanager().get_chunk_data(chunkid)

    return {"chunk": chunk_data}


def receive_rpc_download_image(data, *args, **kwargs):
    # fixme: image download logic should be much more complex.
    #  - masternode receive image download request, generate unique code and return to the client
    #  - MN has to validate that requestor pastelID is artwork owner pastelID
    #  - if check passed - collect required chunks from other MNs
    #  - assemble image and store it locally
    #  - provide interface for client to poll if image is ready or not.
    image_hash = data['image_hash']
    chunks_db = Chunk.select().where(Chunk.image_hash == image_hash)
    if len(chunks_db) == 0:
        return {
            "status": "ERROR",
            "mgs": "No chunks for given image"
        }
    chunks = [get_chunkmanager().get_chunk_data(int(x.chunk_id)) for x in chunks_db]
    try:
        image_data = luby.decode(chunks)
    except luby.NotEnoughChunks:
        return {
            "status": "ERROR",
            "mgs": "Not enough chunks to reconstruct given image"
        }

    return {
        "status": "SUCCESS",
        "image_data": image_data
    }


def receive_rpc_download_thumbnail(data, *args, **kwargs):
    image_hash = data['image_hash']
    chunks_db = Chunk.select().where(Chunk.image_hash == image_hash, Chunk.stored == True)
    if len(chunks_db) == 0:
        # fixme: maybe if current MN does not stores a given thumbnail - it worth
        #  to return a list of masternodes which should store it (from ChunkMnRanked table).
        try:
            chunk = Chunk.select().get(Chunk.image_hash == image_hash)
        except Exception:
            return {
                "status": "ERROR",
                "msg": "No chunks for given image",
                "masternodes": []
            }

        masternodes = [c.masternode.pastel_id for c in ChunkMnRanked.select().where(ChunkMnRanked.chunk == chunk)]
        return {
            "status": "ERROR",
            "msg": "No chunks for given image",
            "masternodes": masternodes
        }
    if len(chunks_db) > 1:
        return {
            "status": "ERROR",
            "msg": "There {} chunks for thumbnails in DB. should be one.".format(len(chunks_db))
        }

    thumbnail_data = get_chunkmanager().get_chunk_data(int(chunks_db[0].chunk_id))
    # thumbnail is not encoded, so no decore is required.
    return {
        "status": "SUCCESS",
        "image_data": thumbnail_data
    }
