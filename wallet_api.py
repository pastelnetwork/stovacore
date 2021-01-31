import asyncio
import os
import signal
import sys
import logging

from peewee import logger as peewee_logger
from bitcoinrpc.authproxy import log as bitcoinrpc_logger

os.environ['PYNODE_MODE'] = 'WALLET'


from utils.create_wallet_tables import create_tables
from wallet.database import db
from wallet.http_server import run_http_server
from wallet.settings import WALLET_DATABASE_FILE, THUMBNAIL_DIR, get_artwork_dir, get_thumbnail_dir
from wallet.tasks import refresh_masternode_list

APP_DIR = None


async def masternode_refresh():
    while True:
        refresh_masternode_list()
        await asyncio.sleep(10)


def run_event_loop():
    loop = asyncio.get_event_loop()
    try:
        loop.add_signal_handler(signal.SIGTERM, loop.stop)
    except NotImplementedError:
        # add_signal_handler is not implemented for Windows
        pass
    loop.create_task(run_http_server())
    loop.create_task(masternode_refresh())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.stop()


if __name__ == '__main__':
    if len(sys.argv) < 4:
        raise Exception('Usage: ./wallet_api <wallet_dir> <pastelid> <passphrase>')
    peewee_logger.disabled = True
    bitcoinrpc_logger.disabled = True

    app_dir = sys.argv[1]
    pastelid = sys.argv[2]
    passphrase = sys.argv[3]
    os.environ.setdefault('PASTEL_ID', pastelid)
    os.environ.setdefault('PASSPHRASE', passphrase)
    os.environ.setdefault('APP_DIR', app_dir)
    if not os.path.exists(get_artwork_dir()):
        os.mkdir(get_artwork_dir())
    if not os.path.exists(get_thumbnail_dir()):
        os.mkdir(get_thumbnail_dir())
    db.init(os.path.join(app_dir, WALLET_DATABASE_FILE))
    # if not os.path.exists(os.path.join(APP_DIR, WALLET_DATABASE_FILE)):
    create_tables()
    logging.basicConfig(level=logging.INFO)
    run_event_loop()
