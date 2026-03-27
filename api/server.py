import os
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from nox.runtime.engine_runtime import engine

import stripe
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from jose import jwt, JWTError
from pydantic import BaseModel

# NOX
from nox.runtime.engine_runtime import Runtime
from nox.runtime.plugin_loader import load_plugins

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────
load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"

security = HTTPBearer()

# ────────────────────────────────────────────────
# TEMP USER STORE (Replace with DB later)
# ────────────────────────────────────────────────
users_db: dict = {}

# ────────────────────────────────────────────────
# MODELS
# ────────────────────────────────────────────────
class AuthRequest(BaseModel):
    username: str
    password: str


class AutoRechargeRequest(BaseModel):
    enabled: bool


# ────────────────────────────────────────────────
# AUTH HELPERS
# ────────────────────────────────────────────────
def create_token(username: str):
    expire = datetime.utcnow() + timedelta(hours=24)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ────────────────────────────────────────────────
# SAFE STARTUP (NO CRASH)
# ────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 NOX Backend starting...")

    try:
        from database import Base, engine
        Base.metadata.create_all(bind=engine)
        print("✅ Database initialized")
    except Exception as e:
        print("❌ DB INIT FAILED:", str(e))

    yield

    print("🛑 NOX Backend shutting down...")


# ────────────────────────────────────────────────
# APP
# ────────────────────────────────────────────────
app = FastAPI(title="NOX AI Backend", lifespan=lifespan)

# Load runtime
runtime = Runtime()
load_plugins(runtime)

# Static
os.makedirs("exports", exist_ok=True)
app.mount("/exports", StaticFiles(directory="exports"), name="exports")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ────────────────────────────────────────────────
# ROOT
# ────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"status": "running", "service": "NOX AI Backend"}


# ────────────────────────────────────────────────
# AUTH
# ────────────────────────────────────────────────
@app.post("/signup")
async def signup(data: AuthRequest):
    if data.username in users_db:
        raise HTTPException(400, "User exists")

    users_db[data.username] = {
        "password": data.password,
        "credits": 50
    }

    return {"message": "User created"}


@app.post("/login")
async def login(data: AuthRequest):
    user = users_db.get(data.username)

    if not user or user["password"] != data.password:
        raise HTTPException(401, "Invalid credentials")

    return {"token": create_token(data.username)}


# ────────────────────────────────────────────────
# CHAT (TOKEN PROTECTED)
# ────────────────────────────────────────────────

@app.post("/chat")
async def chat(
    data: dict,
    user: str = Depends(get_current_user)   # 👈 this gives username
):
    try:
        prompt = data.get("prompt", "").strip()

        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")

        # ✅ FIX: use user (not user_id)
        result = await engine.handle_prompt(prompt, user_id=user)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ────────────────────────────────────────────────
# STREAM
# ────────────────────────────────────────────────
@app.get("/stream")
async def stream(user=Depends(get_current_user)):
    agent = runtime.get_agent("code_agent")

    if not agent:
        async def empty():
            yield "data: No agent\n\n"
        return StreamingResponse(empty(), media_type="text/event-stream")

    async def generator():
        try:
            async for msg in agent.stream(user):
                yield f"data: {str(msg)}\n\n"
        except Exception as e:
            yield f"data: ERROR {str(e)}\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")


# ────────────────────────────────────────────────
# CREDITS
# ────────────────────────────────────────────────
@app.get("/credits/{user_id}")
async def credits(user_id: str, user=Depends(get_current_user)):
    if user_id != user:
        raise HTTPException(403, "Unauthorized")

    billing = runtime.get_agent("billing_agent")

    if not billing:
        u = users_db.get(user_id, {})
        return {"credits": u.get("credits", 0)}

    return billing._get_user(user_id)


# ────────────────────────────────────────────────
# STRIPE
# ────────────────────────────────────────────────
@app.post("/create-checkout-session")
async def checkout(data: dict, user=Depends(get_current_user)):
    plan = data.get("plan")

    prices = {
        "starter": 500,
        "pro": 2000,
        "mega": 5000
    }

    amount = prices.get(plan)
    if not amount:
        raise HTTPException(400, "Invalid plan")

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": f"{plan} credits"},
                "unit_amount": amount,
            },
            "quantity": 1,
        }],
        success_url="https://your-frontend-url?success=true",
        cancel_url="https://your-frontend-url?cancel=true",
        metadata={"user_id": user, "plan": plan}
    )

    return {"url": session.url}


# ────────────────────────────────────────────────
# AUTO RECHARGE
# ────────────────────────────────────────────────
@app.post("/toggle-auto-recharge")
async def toggle(req: AutoRechargeRequest, user=Depends(get_current_user)):
    billing = runtime.get_agent("billing_agent")

    if not billing:
        return {"status": "no billing agent"}

    billing.set_auto_recharge(user, req.enabled)
    return {"status": "ok"}