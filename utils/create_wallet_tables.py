from wallet.database import db, WALLET_DB_MODELS, Masternode


def create_tables():
    db.connect(reuse_if_open=True)
    db.create_tables(WALLET_DB_MODELS)
    # clear existing MNs.
    Masternode.delete().execute()


# if __name__ == '__main__':
#     if len(sys.argv) < 2:
#         raise Exception('Usage: ./create_wallet_tables <wallet_dir>')
#     APP_DIR = sys.argv[1]
#     db.init(os.path.join(APP_DIR, WALLET_DATABASE_FILE))
#     create_tables()
