import os
import random
import signal
import sys
import base64
import json
from collections import OrderedDict
from PastelCommon.keys import id_keypair_generation_func
from aiohttp import web
from PastelCommon.signatures import pastel_id_write_signature_on_data_func, \
    pastel_id_verify_signature_with_public_key_func

KEY_PATH = 'keys'
APP_DIR = None
routes = web.RouteTableDef()
pastel_client = None

def ordered_json_string_from_dict(data):
    sorted_data = sorted(data.items(), key=lambda x: x[0])
    ordered = OrderedDict(sorted_data)
    return json.dumps(ordered)

def get_pastel_client():
    global pastel_client
    if pastel_client is None:
        from core_modules.djangointerface import DjangoInterface
        pastel_client = DjangoInterface(private_key, public_key, None, None, None, None)
    return pastel_client


def generate_key_id():
    key_id = random.randint(10000, 99999)
    while os.path.exists(os.path.join(KEY_PATH, 'private_{}.key'.format(key_id))):
        key_id = random.randint(10000, 99999)
    return key_id


def check_or_generate_keys(app_dir):
    __privkey, __pubkey = id_keypair_generation_func()
    key_path = os.path.join(app_dir, KEY_PATH)
    if not os.path.exists(key_path):
        os.mkdir(key_path)

    if not os.path.exists(os.path.join(key_path, 'private.key')):
        with open(os.path.join(key_path, 'private.key'), "wb") as f:
            f.write(__privkey)
        os.chmod(os.path.join(key_path, 'private.key'), 0o0700)
        with open(os.path.join(key_path, 'public.key'), "wb") as f:
            f.write(__pubkey)
        os.chmod(os.path.join(key_path, 'public.key'), 0o0700)

def generate_pastel_keys():
    __privkey, __pubkey = id_keypair_generation_func()

    privkey = 'private.key'
    pubkey = 'public.key'
    if not os.path.exists(KEY_PATH):
        os.mkdir(KEY_PATH)
    with open(os.path.join(KEY_PATH, privkey), "wb") as f:
        f.write(__privkey)
    os.chmod(os.path.join(KEY_PATH, privkey), 0o0700)
    with open(os.path.join(KEY_PATH, pubkey), "wb") as f:
        f.write(__pubkey)
    os.chmod(os.path.join(KEY_PATH, pubkey), 0o0700)


@routes.get('/generate_keys')
async def generate_keys(request):
    if os.path.exists(os.path.join(KEY_PATH, 'private.key')) and os.path.exists(os.path.join(KEY_PATH, 'public.key')):
        return web.json_response({
            'private': os.path.join(KEY_PATH, 'private.key'),
            'public': os.path.join(KEY_PATH, 'public.key')
        })

    generate_pastel_keys()
    return web.json_response({
        'private': os.path.join(KEY_PATH, privkey),
        'public': os.path.join(KEY_PATH, pubkey)
    })

@routes.get('/get_keys')
async def get_keys(request):
    return web.json_response({
        'private': os.path.join(APP_DIR, KEY_PATH, 'private.key'),
        'public': os.path.join(APP_DIR, KEY_PATH, 'public.key')
    })



@routes.post('/sign_message')
async def sign_message(request):
    global public_key
    str_pk = base64.encodebytes(public_key).decode()
    data = await request.json()
    string_data = ordered_json_string_from_dict(data)
    bytes_data = string_data.encode()
    signature = pastel_id_write_signature_on_data_func(bytes_data, private_key, public_key)
    signature_string = base64.encodebytes(signature).decode()

    # signature_restored = base64.b64decode(signature_string.encode())
    # pk_restored = base64.b64decode(str_pk.encode())
    # verified = pastel_id_verify_signature_with_public_key_func(bytes_data, signature_restored, pk_restored)
    return web.json_response({'signature': signature_string,
                              'pastel_id': str_pk})

@routes.get('/get_base64_pastel_id')
async def get_base64_pastel_id(request):
    global public_key
    str_pk = base64.encodebytes(public_key).decode()
    return web.json_response({'pastel_id': str_pk})


@routes.get('/verify_signature')
async def verify_signature(request):
    return web.json_response({'method': 'verify_signature'})


@routes.post('/register_image')
async def register_image(request):
    # TODO: get and adjust implementation from djangointerface.py
    global pastel_client
    data = await request.post()
    image = data['image']
    filename = image.filename
    image_file = image.file
    content = image_file.read()

    await get_pastel_client().register_image(filename, content)
    return web.json_response({'method': 'register_image', 'title': filename})


app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise Exception('Usage: ./wallet_api <wallet_dir>')
    APP_DIR = sys.argv[1]
    check_or_generate_keys(APP_DIR)
    with open(os.path.join(APP_DIR, KEY_PATH, 'private.key'), "rb") as f:
        private_key = f.read()

    with open(os.path.join(APP_DIR, KEY_PATH, 'public.key'), "rb") as f:
        public_key = f.read()

    web.run_app(app, port=5000)
    app.loop.add_signal_handler(signal.SIGINT, app.loop.stop)
