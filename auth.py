from database import SessionLocal
from models import User as DBUser

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()