from flask import Flask, jsonify
import os
import random
from PastelCommon.keys import id_keypair_generation_func
from PastelCommon.signatures import pastel_id_write_signature_on_data_func, \
    pastel_id_verify_signature_with_public_key_func

KEY_PATH = 'keys'

app = Flask(__name__)


def generate_key_id():
    key_id = random.randint(10000, 99999)
    while os.path.exists(os.path.join(KEY_PATH, 'private_{}.key'.format(key_id))):
        key_id = random.randint(10000, 99999)
    return key_id


@app.route('/generate_keys', methods=['GET'])
def generate_keys():
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
    return jsonify({
        'private': os.path.join(KEY_PATH, privkey),
        'public': os.path.join(KEY_PATH, pubkey)
    })


@app.route('/sign_message', methods=['GET'])
def sign_message():
    return jsonify({'method': 'sign_message'})


@app.route('/verify_signature', methods=['GET'])
def verify_signature():
    return jsonify({'method': verify_signature})


@app.route('/register_image', methods=['GET'])
def register_image():
    # TODO: get and adjust implementation from djangointerface.py
    return jsonify({'method': register_image})


if __name__ == '__main__':
    app.run(debug=True)
