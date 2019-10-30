from core_modules.database import MASTERNODE_DB, DB_MODELS
from core_modules.settings import NetWorkSettings

MASTERNODE_DB.init(NetWorkSettings.MN_DATABASE_FILE)
MASTERNODE_DB.connect(reuse_if_open=True)
MASTERNODE_DB.create_tables(DB_MODELS)
