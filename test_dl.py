import os
import asyncio
import logging
from wallet.database import db, RegticketDB

db.init('/Users/alex/PycharmProjects/spa/wallet.db')

image_hash = b'\xeaW\xc4\xab\x90\xd3\xb3\xa0\xb6\xfc\xbf\xc6\x9f\x9d\xc0>+\x81\x84\xf2\x7f\xf2\xbe:\xa3\x84\x9d~l\'\xf8\x9c\r\x89\x8cX\xcb5\x83I\xea\xd2>E\xf7\x9d\x88\xf8\t\xb9_\xb4"\x84H\xde\xca$\xccD\x1a\x05=\x8b'

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
