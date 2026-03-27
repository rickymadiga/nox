from sqlalchemy import Column, Integer, String
from database import Base   # ✅ THIS FIX

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    password = Column(String)