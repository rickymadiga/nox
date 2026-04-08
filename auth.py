from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User
from passlib.context import CryptContext
from jose import jwt
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import time


router = APIRouter()
security = HTTPBearer(auto_error=False)  # Make it optional if needed
SECRET_KEY = os.getenv("SECRET_KEY", "supersecret")
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─────────────────────────────
# MODELS
# ─────────────────────────────
class AuthRequest(BaseModel):
    username: str
    password: str

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # 🔥 DEV BYPASS - Accept any dev_ prefixed token
    if token.startswith("dev_"):
        # Extract username from token (dev_admin_1744...)
        try:
            username = token.split("_")[1]
            return {"user_id": username, "is_dev": True}
        except:
            pass

    # ← Your normal JWT / token validation code goes here
    # e.g. decode JWT, check DB, etc.
    # ...

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

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