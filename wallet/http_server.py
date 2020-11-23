import os
import sys
from aiohttp import web
from bitcoinrpc.authproxy import JSONRPCException

from wallet.database import RegticketDB
from wallet.settings import get_artwork_dir

routes = web.RouteTableDef()
pastel_client = None

def get_pastel_client():
    # this import should be local to let env varibles be set earlier than blockchain object will be created
    # global blockchain object uses env variables for getting pastelID and passphrase
    from wallet.pastel_client import PastelClient
    global pastel_client
    pastelid = os.environ['PASTEL_ID']
    passphrase = os.environ['PASSPHRASE']

    if pastel_client is None:
        pastel_client = PastelClient(pastelid, passphrase)
    return pastel_client


@routes.post('/image_registration_step_2')
async def image_registration_step_2(request):
    """
    - Send regticket to MN0
    - Receive upload_code
    - Upload image
    - Receive worker's fee
    - Store regticket metadata to loca db
    Input {image: path_to_image_file, title: image_title}
    Returns {workers_fee, regticket_id}
    """
    # FIXME: current input from electron
    #  Document
    #  Pass this data further
    """
        const pyApiData = {
        image: data.filePath,
        title: data.name,
        num_copies: data.numCopies,
        copy_price: data.copyPrice
    };
    """
    data = await request.json()
    image_path = data.pop('image')
    with open(image_path, 'rb') as f:
        content = f.read()
    # try:
    result = await get_pastel_client().image_registration_step_2(regticket_data=data, image_data=content)
    # except Exception as ex:
    #     return web.json_response({'error': str(ex)}, status=400)
    regticket_db = RegticketDB.get(RegticketDB.id == result['regticket_id'])
    regticket_db.path_to_image = image_path
    regticket_db.save()
    print('Fee received: {}'.format(result['worker_fee']))
    return web.json_response({'fee': result['worker_fee'], 'regticket_id': regticket_db.id})


@routes.post('/image_registration_step_3')
async def image_registration_step_3(request):
    """
    - Send regticket to mn2, get upload code, upload image to mn2
    - Send regticket to mn3, get upload code, upload image to mn3
    - Verify both MNs accepted images - then return success, else return error
    Input {regticket_id: id}
    Returns transaction id, success/fail
    """
    data = await request.json()
    regticket_id = data['regticket_id']

    response = await get_pastel_client().image_registration_step_3(regticket_id)
    # return ticket height ticket fee pastelid and passphrase
    print('Img registration step 3 response: {}'.format(response), file=sys.stderr)
    return web.json_response(response)


@routes.post('/image_registration_cancel')
async def image_registration_cancel(request):
    """
    Input {regticket_id}
    """
    data = await request.json()
    RegticketDB.get(RegticketDB.id == data['regticket_id']).delete_instance()
    return web.json_response({})


@routes.post('/download_image')
async def download_image(request):
    """
    Input {regticket_id}  - id from local DB.
    """
    data = await request.json()
    regticket_db = RegticketDB.get(RegticketDB.id == data['regticket_id'])
    response = await get_pastel_client().download_image(regticket_db.image_hash)
    if response is not None:
        filename = os.path.join(get_artwork_dir(), '{}.jpg'.format(data['regticket_id']))
        with open(filename, 'wb') as f:
            f.write(response)
        return web.json_response({'status': 'SUCCESS', 'filename': filename})
    return web.json_response({'status': 'error', 'msg': 'Image not found on masternodes'})


@routes.post('/create_sell_ticket')
async def create_sell_ticket(request):
    data = await request.json()
    # data is expected to be {'txid': <txid>, 'price': <price>, 'image_hash': <image_hash>}
    # FIXME: why not add validation for wallet_api? wallet app error on API calls should be visible in the
    #  wallet, at least in wallet console
    try:
        response = await get_pastel_client().register_sell_ticket(**data)
    except JSONRPCException as ex:
        return web.json_response({'error': str(ex)}, status=400)

    # returning same image hash as we received to associate this response with a given artwork for node process.
    return web.json_response({'txid': response})


@routes.get('/artworks_data')
async def artworks_data(request):
    # try:
    artwork_data = await get_pastel_client().get_artworks_data()
    # except Exception as ex:
    #     return web.json_response({'error': 'Unable to fetch artworks data, try again later'}, status=503)
    return web.json_response(artwork_data)


@routes.post('/ping')
async def ping(request):
    get_pastel_client()
    return web.json_response({})


app = web.Application()
app.add_routes(routes)


async def run_http_server():
    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, port=5000)
    await site.start()
