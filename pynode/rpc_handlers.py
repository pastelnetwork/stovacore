from core_modules.blackbox_modules import luby
from core_modules.chunkmanager import get_chunkmanager
from core_modules.database import Chunk
from core_modules.helpers import hex_to_chunkid
from core_modules.logger import initlogging
from core_modules.rpc_client import RPCException

rpc_handler_logger = initlogging('RPCHandlerLogger', __name__)


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
