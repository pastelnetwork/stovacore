from core_modules.database import db, Regticket, Chunk

db.connect(reuse_if_open=True)
db.create_tables([Regticket, Chunk])
