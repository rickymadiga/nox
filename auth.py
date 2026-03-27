from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User
from passlib.context import CryptContext
from jose import jwt
import os

router = APIRouter()

SECRET_KEY = os.getenv("SECRET_KEY", "supersecret")
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─────────────────────────────
# MODELS
# ─────────────────────────────
class AuthRequest(BaseModel):
    username: str
    password: str


# ─────────────────────────────
# HELPERS
# ─────────────────────────────
def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(password, hashed):
    return pwd_context.verify(password, hashed)

def create_token(username: str):
    return jwt.encode({"sub": username}, SECRET_KEY, algorithm=ALGORITHM)


# ─────────────────────────────
# SIGNUP
# ─────────────────────────────
@router.post("/signup")
def signup(data: AuthRequest):
    db: Session = SessionLocal()

    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(
        username=data.username,
        password=hash_password(data.password)
    )

    db.add(user)
    db.commit()

    return {"message": "User created successfully"}


# ─────────────────────────────
# LOGIN
# ─────────────────────────────
@router.post("/login")
def login(data: AuthRequest):
    db: Session = SessionLocal()

    user = db.query(User).filter(User.username == data.username).first()

    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(user.username)

    return {"token": token}