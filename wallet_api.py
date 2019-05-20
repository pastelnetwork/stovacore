import os
import random
import signal
from PastelCommon.keys import id_keypair_generation_func
from aiohttp import web
from PastelCommon.signatures import pastel_id_write_signature_on_data_func, \
    pastel_id_verify_signature_with_public_key_func
from core_modules.djangointerface import DjangoInterface

KEY_PATH = 'keys'

routes = web.RouteTableDef()

def generate_key_id():
    key_id = random.randint(10000, 99999)
    while os.path.exists(os.path.join(KEY_PATH, 'private_{}.key'.format(key_id))):
        key_id = random.randint(10000, 99999)
    return key_id

__privkey, __pubkey = id_keypair_generation_func()

if not os.path.exists(KEY_PATH):
    os.mkdir(KEY_PATH)

if not os.path.exists(os.path.join(KEY_PATH, 'private.key')):
    with open(os.path.join(KEY_PATH, 'private.key'), "wb") as f:
        f.write(__privkey)
    os.chmod(os.path.join(KEY_PATH, 'private.key'), 0o0700)
    with open(os.path.join(KEY_PATH, 'public.key'), "wb") as f:
        f.write(__pubkey)
    os.chmod(os.path.join(KEY_PATH, 'public.key'), 0o0700)

with open(os.path.join(KEY_PATH, 'private.key'), "rb") as f:
    private_key = f.read()

with open(os.path.join(KEY_PATH, 'public.key'), "rb") as f:
    public_key = f.read()


pastel_client = DjangoInterface(private_key, public_key, None, None, None, None)


@routes.get('/generate_keys')
async def generate_keys(request):
    __privkey, __pubkey = id_keypair_generation_func()
    key_id = generate_key_id()
    privkey = 'private_{}.key'.format(key_id)
    pubkey = 'public_{}.key'.format(key_id)
    if not os.path.exists(KEY_PATH):
        os.mkdir(KEY_PATH)
    with open(os.path.join(KEY_PATH, privkey), "wb") as f:
        f.write(__privkey)
    os.chmod(os.path.join(KEY_PATH, privkey), 0o0700)
    with open(os.path.join(KEY_PATH, pubkey), "wb") as f:
        f.write(__pubkey)
    os.chmod(os.path.join(KEY_PATH, pubkey), 0o0700)
    return web.json_response({
        'private': os.path.join(KEY_PATH, privkey),
        'public': os.path.join(KEY_PATH, pubkey)
    })


@routes.get('/sign_message')
async def sign_message(request):
    return web.json_response({'method': 'sign_message'})


@routes.get('/verify_signature')
async def verify_signature(request):
    return web.json_response({'method': 'verify_signature'})


@routes.post('/register_image')
async def register_image(request):
    # TODO: get and adjust implementation from djangointerface.py
    data = await request.post()
    image = data['image']
    filename = image.filename
    image_file = image.file
    content = image_file.read()

    await pastel_client.register_image(filename, content)
    return web.json_response({'method': 'register_image', 'title': filename})


app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
    web.run_app(app, port=5000)
    app.loop.add_signal_handler(signal.SIGINT, app.loop.stop)
