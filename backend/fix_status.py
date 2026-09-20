from app.db import SessionLocal
from app.models.seller import Seller
db = SessionLocal()
for s in db.query(Seller).all():
    s.status = 'ACTIVE'
    s.marketplace_status = 'PUBLISHED'
db.commit()
print("Fixed!")
