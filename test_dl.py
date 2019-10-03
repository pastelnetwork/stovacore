import os
import asyncio
import logging

imagedata_hash = b'\x05\x14\xc6\x05v\xab\x13\xe2\xb1K\x81\xd3\x9f\xa7\xc6\xc1\xc7\xe0\xed\xb0\xee\xc101"\x88\xe9\xf7\xbb\xfcB\x95!(\xd1+)\xad\xa6W\xd4\xfaZ\xfd\xe2\xda_T=\xe2\x0ft\x1fP(\x93\x8efJ\xd9\xd9\xb1J\x1b'

os.environ.setdefault('PASTEL_ID',
                      'jXZghafefxPUfkWesi4qUKrpkPfAsG9QiGDBYUcdTxuyg1XpwbZrzYQrjdJSLPwL8BGGdriLk3azkBiMcSHhw6')
os.environ.setdefault('PASSPHRASE', 'taksa')

from wallet.pastel_client import PastelClient

logging.basicConfig(level=logging.DEBUG)

client = PastelClient("jXZghafefxPUfkWesi4qUKrpkPfAsG9QiGDBYUcdTxuyg1XpwbZrzYQrjdJSLPwL8BGGdriLk3azkBiMcSHhw6", "taksa")

# await client.download_image(imagedata_hash)

loop = asyncio.get_event_loop()


loop.create_task(client.download_image(imagedata_hash))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass
finally:
    # FIXME: such stopping create infinite recursion. Need to close port when stopping.
    # loop.run_until_complete(self.logic.stop_rpc_server())
    loop.stop()
