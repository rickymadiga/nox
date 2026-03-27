import os
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

import stripe
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from jose import jwt, JWTError
from pydantic import BaseModel

# NOX specific
from nox.runtime.engine_runtime import Runtime
from nox.runtime.plugin_loader import load_plugins

# ────────────────────────────────────────────────
# CONFIG & ENVIRONMENT
# ────────────────────────────────────────────────
load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# TODO: Change this in production! Use a strong secret from env
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"

security = HTTPBearer()

# ────────────────────────────────────────────────
# FAKE DB (Replace with real Postgres later)
# ────────────────────────────────────────────────
users_db: dict = {}  # username -> user dict

# ────────────────────────────────────────────────
# PYDANTIC MODELS
# ────────────────────────────────────────────────
class AuthRequest(BaseModel):
    username: str
    password: str


class AutoRechargeRequest(BaseModel):
    enabled: bool


# ────────────────────────────────────────────────
# AUTH HELPERS
# ────────────────────────────────────────────────
def create_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode = {"sub": username, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ────────────────────────────────────────────────
# LIFESPAN
# ────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 NOX Backend starting...")

    # Create tables (if using real DB)
    from database import Base, engine
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")

    yield
    print("🛑 NOX Backend shutting down...")


# ────────────────────────────────────────────────
# APP INITIALIZATION
# ────────────────────────────────────────────────
app = FastAPI(title="NOX AI Backend", lifespan=lifespan)

# Include external routers
from auth import router as auth_router
app.include_router(auth_router)

# Mount static exports
os.makedirs("exports", exist_ok=True)
app.mount("/exports", StaticFiles(directory="exports"), name="exports")

# Initialize NOX runtime
runtime = Runtime()
load_plugins(runtime)

# ────────────────────────────────────────────────
# CORS
# ────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ────────────────────────────────────────────────
# ROOT ENDPOINT
# ────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "service": "NOX AI Backend",
        "status": "running",
        "version": "3.0"
    }

# ────────────────────────────────────────────────
# AUTH ROUTES
# ────────────────────────────────────────────────
@app.post("/signup")
async def signup(data: AuthRequest):
    if data.username in users_db:
        raise HTTPException(status_code=400, detail="User already exists")

    users_db[data.username] = {
        "password": data.password,   # TODO: Hash password in production!
        "credits": 50
    }

    return {"message": "User created successfully"}


@app.post("/login")
async def login(data: AuthRequest):
    user = users_db.get(data.username)
    if not user or user.get("password") != data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(data.username)
    return {"token": token}


# ────────────────────────────────────────────────
# CHAT ENDPOINT (Updated with your requested block)
# ────────────────────────────────────────────────
@app.post("/chat")
async def chat(
    data: dict,
    user=Depends(get_current_user)   # Your preferred simple style
):
    try:
        prompt = data.get("prompt", "").strip()
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")

        user_id = user  # 🔥 real authenticated user from token

        # Using runtime as base (consistent with other endpoints)
        result = await runtime.engine.handle_prompt(prompt, user_id=user_id)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ────────────────────────────────────────────────
# LOGS & STREAMING
# ────────────────────────────────────────────────
@app.get("/logs")
async def get_logs(user_id: str = Depends(get_current_user)):
    code_agent = runtime.get_agent("code_agent")
    if not code_agent:
        return {"logs": []}

    try:
        logs = await code_agent.run({"user_id": user_id})
        return {"logs": logs}
    except Exception:
        return {"logs": []}


@app.get("/stream")
async def stream_logs(user_id: str = Depends(get_current_user)):
    code_agent = runtime.get_agent("code_agent")
    if not code_agent:
        async def empty_generator():
            yield "data: [No code_agent available]\n\n"
        return StreamingResponse(empty_generator(), media_type="text/event-stream")

    async def event_generator():
        try:
            async for message in code_agent.stream(user_id):
                msg = str(message.get("message", message) if isinstance(message, dict) else message)
                yield f"data: {msg}\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


# ────────────────────────────────────────────────
# CREDITS & BILLING
# ────────────────────────────────────────────────
@app.get("/credits/{user_id}")
async def get_credits(
    user_id: str,
    current_user: str = Depends(get_current_user)
):
    if user_id != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    billing = runtime.get_agent("billing_agent")
    if not billing:
        user = users_db.get(user_id, {})
        return {
            "credits": user.get("credits", 0),
            "plan": "free",
            "is_admin": False
        }

    user = billing._get_user(user_id)
    return {
        "credits": user.get("credits", 0),
        "plan": user.get("plan", "free"),
        "is_admin": user.get("is_admin", False)
    }


# ────────────────────────────────────────────────
# STRIPE CHECKOUT
# ────────────────────────────────────────────────
@app.post("/create-checkout-session")
async def create_checkout(
    payload: dict,
    user_id: str = Depends(get_current_user)
):
    try:
        plan = payload.get("plan", "").lower()
        price_map = {
            "starter": 500,
            "pro": 2000,
            "mega": 5000
        }

        amount = price_map.get(plan)
        if not amount:
            raise HTTPException(status_code=400, detail="Invalid plan")

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"{plan.title()} Credits"},
                    "unit_amount": amount,
                },
                "quantity": 1,
            }],
            success_url="http://localhost:8501?success=true",
            cancel_url="http://localhost:8501?cancel=true",
            metadata={"user_id": user_id, "plan": plan}
        )

        return {"url": session.url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ────────────────────────────────────────────────
# AUTO RECHARGE
# ────────────────────────────────────────────────
@app.post("/toggle-auto-recharge")
async def toggle_auto_recharge(
    req: AutoRechargeRequest,
    user_id: str = Depends(get_current_user)
):
    billing = runtime.get_agent("billing_agent")
    if not billing:
        return {"status": "error", "detail": "Billing agent not available"}

    billing.set_auto_recharge(user_id, req.enabled)
    return {"status": "ok"}


# ────────────────────────────────────────────────
# ADMIN
# ────────────────────────────────────────────────
@app.get("/admin/dashboard")
async def admin_dashboard():
    admin = runtime.get_agent("admin_agent")
    if not admin:
        raise HTTPException(status_code=503, detail="Admin agent not loaded")
    return admin.get_dashboard()