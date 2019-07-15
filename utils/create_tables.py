from core_modules.database import db, UploadCode

db.connect(reuse_if_open=True)
db.create_tables([UploadCode])
