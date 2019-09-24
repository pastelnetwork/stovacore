import os
import asyncio
import json
from wallet.pastel_client import DjangoInterface

APP_DIR = '/Users/alex/PycharmProjects/spa'
KEY_PATH = 'keys'

with open('masternodes.conf', 'r') as f:
    masternodes = json.loads(f.read())

with open(os.path.join(APP_DIR, KEY_PATH, 'private.key'), "rb") as f:
    private_key = f.read()

with open(os.path.join(APP_DIR, KEY_PATH, 'public.key'), "rb") as f:
    public_key = f.read()

pastel_client = DjangoInterface(private_key, public_key, None, None, None)

# mn0, mn1, mn2 = pastel_client._DjangoInterface__nodemanager.get_rpc_client_for_masternode(masternodes)

clients = dict()

exclude = {}  # {'mn6'}

result = {}


async def main():
    print('start')
    for node in masternodes:
        k = list(node.keys())[0]
        if k in exclude:
            print('Skipping {}'.format(k))
            continue
        print('Masternode {}'.format(k))
        if k not in clients:
            clients[k] = pastel_client._DjangoInterface__nodemanager.get_rpc_client_for_masternode(node[k])
        resp = await clients[k].send_rpc_ping(b'Krot')
        if resp is None:
            result[k] = 'Timeout'
        else:
            result[k] = 'ok'
        print(resp)
    print('Done')
    print(result)

asyncio.run(main())