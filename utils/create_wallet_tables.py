import sys
import os
from wallet.database import db, RegticketDB, Masternode
from wallet.settings import WALLET_DATABASE_FILE


def create_tables():
    db.connect(reuse_if_open=True)
    db.create_tables([RegticketDB, Masternode])


# if __name__ == '__main__':
#     if len(sys.argv) < 2:
#         raise Exception('Usage: ./create_wallet_tables <wallet_dir>')
#     APP_DIR = sys.argv[1]
#     db.init(os.path.join(APP_DIR, WALLET_DATABASE_FILE))
#     create_tables()
