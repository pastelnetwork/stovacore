import os
import asyncio
import logging
from wallet.database import db, RegticketDB

db.init('/Users/alex/PycharmProjects/spa/wallet.db')

image_hash = b'.\x00\xdc\x10\xee9\x96J`\xef\x0fn\x8c\xe3\x04\x9e\xe1\r\x94\xb5f)\xbc\x1aJ_\xc3\xd3u)x\x89\x8aa\x00\xb7!\xf9\xd3i\xc1\x0b\xd4\x8e\xd7\xc7\x10\xd5\xe6\x0e\xf8\xfc\x96\xff\x17\x01\x9b\xea+\n\x00\x900Z'

os.environ.setdefault('PASTEL_ID',
                      'jXZghafefxPUfkWesi4qUKrpkPfAsG9QiGDBYUcdTxuyg1XpwbZrzYQrjdJSLPwL8BGGdriLk3azkBiMcSHhw6')
os.environ.setdefault('PASSPHRASE', 'taksa')

from wallet.pastel_client import PastelClient

logging.basicConfig(level=logging.DEBUG)

client = PastelClient("jXZghafefxPUfkWesi4qUKrpkPfAsG9QiGDBYUcdTxuyg1XpwbZrzYQrjdJSLPwL8BGGdriLk3azkBiMcSHhw6", "taksa")

# await client.download_image(imagedata_hash)

loop = asyncio.get_event_loop()


loop.create_task(client.download_image(image_hash))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass
finally:
    # FIXME: such stopping create infinite recursion. Need to close port when stopping.
    # loop.run_until_complete(self.logic.stop_rpc_server())
    loop.stop()
