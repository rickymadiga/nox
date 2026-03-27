import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

print("DATABASE_URL.", os.getenv("DATABASE_URL"))

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL is not set")

# 🔥 FIX for postgres:// bug (Render sometimes gives this)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ✅ ENGINE (your upgrade here)
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # 🔥 prevents broken connections
    future=True
)

# ✅ SESSION
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)