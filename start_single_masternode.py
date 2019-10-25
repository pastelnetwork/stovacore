from core_modules.database import db
from core_modules.settings import NetWorkSettings
from masternode_prototype.masternode_daemon import MasterNodeDaemon


if __name__ == "__main__":
    # initialize the database
    db.init(NetWorkSettings.MN_DATABASE_FILE)
    mnd = MasterNodeDaemon()
    mnd.run_event_loop()
