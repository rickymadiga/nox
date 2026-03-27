import stripe
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from jose import jwt
from pydantic import BaseModel

from nox.runtime.engine_runtime import Runtime, engine
from nox.runtime.plugin_loader import load_plugins

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────
load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

SECRET_KEY = "supersecretkey"  # 🔥 CHANGE IN PROD
ALGORITHM = "HS256"

security = HTTPBearer()

# ────────────────────────────────────────────────
# FAKE DATABASE (REPLACE WITH POSTGRES)
# ────────────────────────────────────────────────
users_db = {}

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
    return jwt.encode(
        {
            "sub": username,
            "exp": datetime.utcnow() + timedelta(hours=24)
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ────────────────────────────────────────────────
# APP INIT
# ────────────────────────────────────────────────
os.makedirs("exports", exist_ok=True)

app = FastAPI(title="NOX AI Backend")

app.mount("/exports", StaticFiles(directory="exports"), name="exports")

runtime = Runtime()
load_plugins(runtime)

# ────────────────────────────────────────────────
# CORS
# ────────────────────────────────────────────────
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
        "password": data.password,
        "credits": 50
    }

    return {"message": "User created"}


@app.post("/login")
async def login(data: AuthRequest):
    user = users_db.get(data.username)

    if not user or user["password"] != data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(data.username)

    return {"token": token}

# ────────────────────────────────────────────────
# CHAT (SECURE)
# ────────────────────────────────────────────────
@app.post("/chat")
async def chat(
    data: dict,
    user_id: str = Depends(get_current_user)
):
    try:
        prompt = data.get("prompt", "")

        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")

        result = await engine.handle_prompt(prompt, user_id=user_id)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ────────────────────────────────────────────────
# LOGS
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

# ────────────────────────────────────────────────
# STREAM (SSE)
# ────────────────────────────────────────────────
@app.get("/stream")
async def stream_logs(user_id: str = Depends(get_current_user)):
    code_agent = runtime.get_agent("code_agent")

    async def event_generator():
        try:
            async for message in code_agent.stream(user_id):
                if isinstance(message, dict):
                    message = str(message.get("message", message))
                yield f"data: {message}\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

# ────────────────────────────────────────────────
# CREDITS (SECURE)
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
        return {"credits": users_db.get(user_id, {}).get("credits", 0)}

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
        plan = payload.get("plan")

        price_map = {
            "starter": 500,
            "pro": 2000,
            "mega": 5000
        }

        amount = price_map.get(plan.lower())

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
        return {"status": "error"}

    billing.set_auto_recharge(user_id, req.enabled)
    return {"status": "ok"}

# ────────────────────────────────────────────────
# ADMIN
# ────────────────────────────────────────────────
@app.get("/admin/dashboard")
async def admin_dashboard():
    admin = runtime.get_agent("admin_agent")
    return admin.get_dashboard()

# ────────────────────────────────────────────────
# STARTUP
# ────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    print("🚀 NOX Backend started")