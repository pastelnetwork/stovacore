import os

WALLET_DATABASE_FILE = 'wallet.db'
BURN_ADDRESS = 'tPXrySyFRrodQeFiTgMoDutf6DTsH6pADJW'

DEBUG = False
THUMBNAIL_DIR = 'thumbnails'
ARTWORKS_DIR_NAME = 'artworks'


def get_artwork_dir():
    return os.path.join(os.environ['APP_DIR'], ARTWORKS_DIR_NAME)


def get_thumbnail_dir():
    return os.path.join(os.environ['APP_DIR'], THUMBNAIL_DIR)

