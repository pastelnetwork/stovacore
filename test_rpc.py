import asyncio

from core_modules.database import MASTERNODE_DB
from core_modules.settings import NetWorkSettings

from core_modules.database import Masternode

MASTERNODE_DB.init(NetWorkSettings.MN_DATABASE_FILE)


def foo():
    for mn in Masternode.select():
        client = mn.get_rpc_client()
        data = client.send_rpc_ping_sync(b'ping')
        print(data)


async def async_foo():
    for mn in Masternode.select():
        client = mn.get_rpc_client()
        data = await client.send_rpc_ping(b'ping')
        print(data)


# test sync
print('Testing sync request')
foo()


print('Testing async request')
loop = asyncio.get_event_loop()
loop.run_until_complete(async_foo())
loop.close()
print('Finished')
