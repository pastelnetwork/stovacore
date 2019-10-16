import os
import asyncio
import logging
from wallet.database import db, RegticketDB

db.init('/Users/alex/PycharmProjects/spa/wallet.db')

image_hash = b'\xf4\xd0Sf0\xc4w\x08\\\xf1\xc9\xe8\xb6\xbbQ\x9b\xac\x935\xabM}\x18\x81\xb1O\xcd]\xe1\x93\xeb@`\xde \x10\xa2\xe8 \x98\x86\x0f"\xd5\x120\xa239\xcf\x10\xe3;{\x8c.]\xd8e\xa4\xa7`*\x8b'

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
