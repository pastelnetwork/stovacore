import os
import random
import asyncio
from PastelCommon.keys import id_keypair_generation_func
from aiohttp import web
from PastelCommon.signatures import pastel_id_write_signature_on_data_func, \
    pastel_id_verify_signature_with_public_key_func

KEY_PATH = 'keys'


def generate_key_id():
    key_id = random.randint(10000, 99999)
    while os.path.exists(os.path.join(KEY_PATH, 'private_{}.key'.format(key_id))):
        key_id = random.randint(10000, 99999)
    return key_id


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


async def sign_message(request):
    return web.json_response({'method': 'sign_message'})


async def verify_signature(request):
    return web.json_response({'method': 'verify_signature'})


async def register_image(request):
    # TODO: get and adjust implementation from djangointerface.py
    return web.json_response({'method': 'register_image'})


async def taksa_handle(request):
    return web.json_response({'taksa': 'krot'})


app = web.Application()
app.add_routes([
    web.get('/generate_keys', generate_keys),
    web.get('/sign_message', sign_message),
    web.get('/verify_signature', verify_signature),
    web.post('/register_image', register_image)
])

if __name__ == '__main__':
    web.run_app(app, port=5000)
