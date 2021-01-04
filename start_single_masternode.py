from core_modules.database import MASTERNODE_DB
from core_modules.settings import Settings
from pynode.masternode_daemon import MasterNodeDaemon
import os.path
from os import path

if __name__ == "__main__":

    if not path.exists(Settings.MN_DATABASE_FILE):
        print("ERROR! Database file doesn't exist - {0}. Create DB or Change value of 'Settings.MN_DATABASE_FILE' "
              "in settings.py " + Settings.MN_DATABASE_FILE)

    # initialize the database
    MASTERNODE_DB.init(Settings.MN_DATABASE_FILE)
    mnd = MasterNodeDaemon()
    mnd.run_event_loop()
