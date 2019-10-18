import os
import asyncio
import logging
from wallet.database import db, RegticketDB

db.init('/Users/alex/PycharmProjects/spa/wallet.db')

image_hash = b'\xca\xc39\xa4n\x8f1\xc4\xdc\x95V\x1e\x87\xa0\\lY\r\xdf\\\\\x18\x95\x8c\\\x95\x1c\xf0\xbd\x85R\xc7\xcb\xd9\x14K;\xfd\xd8\xa7\x8b-\\\xf6T\xd8\x9e\xbf{\xa5\xc3jo\xd0\xec`\xd6Z\x1fZ\x12\xad\xd2\x06'

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
