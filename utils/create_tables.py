from core_modules.database import db, DB_MODELS
from core_modules.settings import NetWorkSettings

db.init(NetWorkSettings.MN_DATABASE_FILE)
db.connect(reuse_if_open=True)
db.create_tables(DB_MODELS)
