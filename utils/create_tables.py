from core_modules.database import MASTERNODE_DB, DB_MODELS
from core_modules.settings import Settings


def create_database():
    MASTERNODE_DB.init(Settings.MN_DATABASE_FILE)
    MASTERNODE_DB.connect(reuse_if_open=True)
    MASTERNODE_DB.create_tables(DB_MODELS)


if __name__ == '__main__':
    create_database()
