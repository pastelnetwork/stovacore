import logging

from core_modules.database import MASTERNODE_DB
from core_modules.settings import Settings
from pynode.masternode_daemon import MasterNodeDaemon

from os import path

from utils.create_tables import create_database

if __name__ == "__main__":

    if not path.exists(Settings.MN_DATABASE_FILE):
        logging.basicConfig(level=logging.DEBUG)
        print("Database file {} does not exist".format(Settings.MN_DATABASE_FILE))
        print("Creating database...")
        create_database()
        print("Database {} created!".format(Settings.MN_DATABASE_FILE))
        # print("ERROR! Database file doesn't exist - {}. Create DB or Change value of 'Settings.MN_DATABASE_FILE' "
        #       "in settings.py ", Settings.MN_DATABASE_FILE)
        # raise SystemExit('Exiting')

    # initialize the database
    MASTERNODE_DB.init(Settings.MN_DATABASE_FILE)

    mnd = MasterNodeDaemon()
    mnd.run_event_loop()
