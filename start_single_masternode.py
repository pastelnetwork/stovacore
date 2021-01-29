from peewee import logger as peewee_logger
from bitcoinrpc.authproxy import log as bitcoinrpc_logger

from core_modules.settings import Settings
from core_modules.database import MASTERNODE_DB
from pynode.masternode_daemon import MasterNodeDaemon

from os import path

from utils.create_tables import create_database

if __name__ == "__main__":
    peewee_logger.disabled = True
    bitcoinrpc_logger.disabled = True

    if not path.exists(Settings.MN_DATABASE_FILE):
        print("Database file {} does not exist".format(Settings.MN_DATABASE_FILE))
        print("Creating database...")
        create_database()
        print("Database {} created!".format(Settings.MN_DATABASE_FILE))

    # initialize the database
    MASTERNODE_DB.init(Settings.MN_DATABASE_FILE)

    mnd = MasterNodeDaemon()
    mnd.run_event_loop()
