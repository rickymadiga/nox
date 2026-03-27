import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# 🚨 HARD FAIL (prevents silent bugs)
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL is not set")

# 🔥 Fix for Render postgres bug
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ✅ ENGINE (UPDATED)
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True
)

# ✅ SESSION
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)