import os
import io
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

import stripe
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from jose import jwt, JWTError
from pydantic import BaseModel

# NOX
from nox.runtime.engine_runtime import engine
from nox.runtime.plugin_loader import load_plugins

# ────────────────────────────────────────────────
# CONFIG & ENVIRONMENT
# ────────────────────────────────────────────────
load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"

security = HTTPBearer()

# ────────────────────────────────────────────────
# GLOBAL INSTANCES
# ────────────────────────────────────────────────
runtime = engine.runtime

# Initialize last_zip storage for in-memory download support
if not hasattr(runtime, "last_zip"):
    runtime.last_zip = None

# ────────────────────────────────────────────────
# TEMP USER STORE (Replace with real DB later)
# ────────────────────────────────────────────────
users_db: dict = {}

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
    return jwt.encode(
        {"sub": username, "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        return payload["sub"]
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )


# ────────────────────────────────────────────────
# LIFESPAN (Safe Startup)
# ────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 NOX Backend starting...")

    try:
        from database import Base, engine as db_engine
        Base.metadata.create_all(bind=db_engine)
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ DB INIT FAILED: {e}")

    yield

    print("🛑 NOX Backend shutting down...")


# ────────────────────────────────────────────────
# FASTAPI APP
# ────────────────────────────────────────────────
app = FastAPI(title="NOX AI Backend", lifespan=lifespan)

# Load plugins
load_plugins(runtime)

# Static files
os.makedirs("exports", exist_ok=True)
app.mount("/exports", StaticFiles(directory="exports"), name="exports")

# Create generated_apps directory for downloads
os.makedirs("generated_apps", exist_ok=True)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ────────────────────────────────────────────────
# ROOT
# ────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "service": "NOX AI Backend",
        "status": "running",
        "version": "3.0"
    }


# ────────────────────────────────────────────────
# DOWNLOAD ENDPOINTS
# ────────────────────────────────────────────────

@app.get("/download/{project}")
def download_project(project: str):
    """Download generated project as ZIP file from disk"""
    zip_path = f"generated_apps/{project}.zip"

    if not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="Project file not found")

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"{project}.zip"
    )


@app.get("/download/latest")
async def download_latest():
    """Download the most recently generated project as bytes (for Streamlit st.download_button)"""
    if not hasattr(runtime, "last_zip") or runtime.last_zip is None:
        raise HTTPException(status_code=404, detail="No recent project available")

    data = runtime.last_zip

    return StreamingResponse(
        io.BytesIO(data["bytes"]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={data['filename']}"
        }
    )


# ────────────────────────────────────────────────
# AUTH ROUTES
# ────────────────────────────────────────────────
@app.post("/signup")
async def signup(data: AuthRequest):
    if data.username in users_db:
        raise HTTPException(status_code=400, detail="User already exists")

    users_db[data.username] = {
        "password": data.password,   # TODO: Hash in production!
        "credits": 50
    }

    return {"message": "User created"}


@app.post("/login")
async def login(data: AuthRequest):
    user = users_db.get(data.username)

    if not user or user.get("password") != data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"token": create_token(data.username)}


# ────────────────────────────────────────────────
# CHAT ENDPOINT
# ────────────────────────────────────────────────
@app.post("/chat")
async def chat(
    data: dict,
    user: str = Depends(get_current_user)
):
    try:
        prompt = data.get("prompt", "").strip()

        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")

        result = await engine.handle_prompt(prompt, user_id=user)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ────────────────────────────────────────────────
# STREAM
# ────────────────────────────────────────────────
@app.get("/stream")
async def stream(user: str = Depends(get_current_user)):
    agent = runtime.get_agent("code_agent")

    if not agent:
        async def empty():
            yield "data: No code_agent available\n\n"
        return StreamingResponse(empty(), media_type="text/event-stream")

    async def generator():
        try:
            async for msg in agent.stream(user):
                yield f"data: {str(msg)}\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")


# ────────────────────────────────────────────────
# CREDITS
# ────────────────────────────────────────────────
@app.get("/credits")
async def get_credits(user: str = Depends(get_current_user)):
    billing = runtime.get_agent("billing_agent")

    if not billing:
        user_data = users_db.get(user, {})
        return {
            "credits": user_data.get("credits", 0),
            "plan": "free",
            "is_admin": False
        }

    user_data = billing._get_user(user)

    return {
        "credits": user_data.get("credits", 0),
        "plan": user_data.get("plan", "free"),
        "is_admin": user_data.get("is_admin", False)
    }


# ────────────────────────────────────────────────
# STRIPE CHECKOUT
# ────────────────────────────────────────────────
@app.post("/create-checkout-session")
async def checkout(data: dict, user: str = Depends(get_current_user)):
    plan = data.get("plan")

    prices = {
        "starter": 500,
        "pro": 2000,
        "mega": 5000
    }

    amount = prices.get(plan)
    if not amount:
        raise HTTPException(status_code=400, detail="Invalid plan")

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
async def toggle(req: AutoRechargeRequest, user: str = Depends(get_current_user)):
    billing = runtime.get_agent("billing_agent")

    if not billing:
        return {"status": "no billing agent"}

    billing.set_auto_recharge(user, req.enabled)
    return {"status": "ok"}