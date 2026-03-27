import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# 🚨 Fail fast if missing
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL is not set")

# 🔥 Fix Render postgres bug
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ✅ Engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True
)

# ✅ Session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ✅ Base (THIS FIXES YOUR ERROR)
Base = declarative_base()