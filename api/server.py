import base64
import hashlib
import hmac
import os
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

import requests
import asyncio
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from dotenv import load_dotenv

# NOX imports
from nox.runtime.engine_runtime import engine
from orchestrator.lily import register as register_lily
from plugins.billing_agent.plugin import register as register_billing
from fastapi import APIRouter

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
REFRESH_SECRET = os.getenv("REFRESH_SECRET", "refreshsecret")
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
DEV_USERS = ["nox", "admin", "cosmic ethic"]
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
runtime = engine.runtime
router = APIRouter(prefix="/nox-u")

if not PAYSTACK_SECRET_KEY:
    print("⚠️  WARNING: PAYSTACK_SECRET_KEY is not set in .env")

# ────────────────────────────────────────────────
# PASSWORD HELPERS
# ────────────────────────────────────────────────
MAX_BCRYPT_BYTES = 72

def normalize_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def _truncate_bcrypt(password: str) -> str:
    encoded = password.encode("utf-8")
    if len(encoded) > 72:
        encoded = encoded[:72]
    return encoded.decode("utf-8",errors="ignore")

def hash_password(password: str) -> str:
    password = normalize_password(password)
    password = _truncate_bcrypt(password)
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    plain_password = normalize_password(plain_password)
    plain_password = _truncate_bcrypt(plain_password)
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


# ────────────────────────────────────────────────
# DATABASE
# ────────────────────────────────────────────────
def init_db():
    with sqlite3.connect("users.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                failed_attempts INTEGER DEFAULT 0,
                lock_until REAL DEFAULT 0,
                auto_recharge INTEGER DEFAULT 0,
                authorization_code TEXT,
                last4 TEXT,
                card_brand TEXT
            )
        """)
        # Safely add columns if they don't exist
        for col in ["auto_recharge", "authorization_code", "last4", "card_brand"]:
            try:
                conn.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT" if col != "auto_recharge" else f"ALTER TABLE users ADD COLUMN {col} INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass

        conn.execute("""
            CREATE TABLE IF NOT EXISTS reset_tokens (
                token TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                expires REAL NOT NULL
            )
        """)
        conn.commit()

    with sqlite3.connect("payments.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                reference TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                credits INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    
    # ───────────────── BUILD HISTORY DB ─────────────────
    with sqlite3.connect("builds.db") as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS builds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            project_name TEXT NOT NULL,
            filename TEXT NOT NULL,
            path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit() 

init_db()

# ────────────────────────────────────────────────
# MODELS
# ────────────────────────────────────────────────
class AuthRequest(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    prompt: str

class RechargeRequest(BaseModel):
    amount: int

class ToggleAutoRechargeRequest(BaseModel):
    enabled: bool

class AutoRechargeRequest(BaseModel):
    amount: int = 500


# ────────────────────────────────────────────────
# AUTH HELPERS
# ────────────────────────────────────────────────
def create_access_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=1)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(days=7)
    return jwt.encode({"sub": username, "exp": expire}, REFRESH_SECRET, algorithm=ALGORITHM)

# ────────────────────────────────────────────────
# UPDATED get_current_user
# ────────────────────────────────────────────────

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        # First try normal JWT decode
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload["sub"]
        
        # Extra safety: mark dev users
        if username in DEV_USERS:
            # You can return more info if needed later
            return username
        
        return username

    except JWTError:
        # Fallback: check if it's somehow a dev token (in case old tokens exist)
        token = credentials.credentials
        if token.startswith("dev_"):
            try:
                username = token.split("_")[1]
                if username in DEV_USERS:
                    return username
            except:
                pass
        
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
# ───────────────── ADMIN GUARD ─────────────────
def require_admin(user: str = Depends(get_current_user)) -> str:
    if user not in ["admin", "nox", "cosmic ethic"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user    


# ────────────────────────────────────────────────
# LIFESPAN
# ────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 NOX Backend starting...")
    register_lily(runtime)
    register_billing(runtime)
    print("AGENTS LOADED:", list(runtime.agents.keys()))
    yield
    print("🛑 Backend shutting down...")


app = FastAPI(lifespan=lifespan)

os.makedirs("generated_apps", exist_ok=True)
app.mount("/exports", StaticFiles(directory="generated_apps"), name="exports")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ────────────────────────────────────────────────
# DEV LOGIN (Fixed - Creates REAL JWT)
# ────────────────────────────────────────────────
class DevLoginRequest(BaseModel):
    username: str

@app.post("/dev_login")
async def dev_login(payload: DevLoginRequest):
    username = payload.username.strip().lower()
    dev_users = ["nox", "admin", "cosmic ethic"]
    
    if username not in dev_users:
        raise HTTPException(status_code=400, detail="Not a valid dev user")

    # Create a REAL JWT token just like normal login
    access_token = create_access_token(username)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": username
    }

# ────────────────────────────────────────────────
# AUTH ENDPOINTS
# ────────────────────────────────────────────────
@app.post("/signup")
async def signup(data: AuthRequest):
    username = data.username.lower().strip()
    if not username or len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")

    hashed = hash_password(data.password)

    with sqlite3.connect("users.db") as conn:
        if conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            raise HTTPException(status_code=400, detail="User already exists")

        conn.execute(
            """INSERT INTO users 
               (username, password, auto_recharge, authorization_code) 
               VALUES (?, ?, 0, NULL)""",
            (username, hashed)
        )
        conn.commit()

    billing = runtime.get_agent("billing_agent")
    if billing:
        billing.get_balance(username)

    return {"message": "Account created successfully"}

@app.post("/login")
async def login(data: AuthRequest):
    username = data.username.lower().strip()

    with sqlite3.connect("users.db") as conn:
        row = conn.execute(
            "SELECT password, failed_attempts, lock_until FROM users WHERE username=?",
            (username,)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    stored_hash, attempts, lock_until = row

    if lock_until and time.time() < lock_until:
        raise HTTPException(status_code=403, detail="Account locked. Try later.")

    if not verify_password(data.password, stored_hash):
        attempts += 1
        lock_time = time.time() + 60 if attempts >= 5 else 0

        with sqlite3.connect("users.db") as conn:
            conn.execute(
                "UPDATE users SET failed_attempts=?, lock_until=? WHERE username=?",
                (attempts, lock_time, username)
            )
            conn.commit()

        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Reset failed attempts
    with sqlite3.connect("users.db") as conn:
        conn.execute(
            "UPDATE users SET failed_attempts=0, lock_until=0 WHERE username=?",
            (username,)
        )
        conn.commit()

    token = create_access_token(username)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": username   # ← This is what frontend expects
    }

# ────────────────────────────────────────────────
# AUTO RECHARGE TOGGLE
# ────────────────────────────────────────────────
@app.post("/toggle-auto-recharge")
async def toggle_auto_recharge(req: ToggleAutoRechargeRequest, user: str = Depends(get_current_user)):
    enabled = 1 if req.enabled else 0

    with sqlite3.connect("users.db") as conn:
        conn.execute(
            "UPDATE users SET auto_recharge = ? WHERE username = ?",
            (enabled, user)
        )
        conn.commit()

    return {"message": f"Auto recharge {'enabled' if req.enabled else 'disabled'} successfully"}


# ────────────────────────────────────────────────
# PAYSTACK INTEGRATION
# ────────────────────────────────────────────────
PRICE_MAP = {
    500:  50000,
    1000: 100000,
    2000: 200000,
    5000: 500000,
}

def get_safe_email(username: str) -> str:
    clean = username.lower().strip()
    clean = ''.join(c if c.isalnum() or c in ['_', '-'] else '_' for c in clean)
    clean = clean.strip('_') or "user"
    return f"{clean}@nox.ai"


@app.post("/paystack/initiate")
async def initiate_payment(req: RechargeRequest, user: str = Depends(get_current_user)):
    if req.amount not in PRICE_MAP:
        raise HTTPException(status_code=400, detail="Invalid amount. Allowed: 500, 1000, 2000, 5000")

    if not PAYSTACK_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Paystack not configured")

    reference = f"nox_{uuid.uuid4().hex[:16]}"
    safe_email = get_safe_email(user)

    with sqlite3.connect("payments.db") as conn:
        conn.execute(
            "INSERT INTO payments (reference, user_id, credits, amount, status) VALUES (?, ?, ?, ?, 'pending')",
            (reference, user, req.amount, req.amount)
        )
        conn.commit()

    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}", "Content-Type": "application/json"}
    payload = {
        "email": safe_email,
        "amount": PRICE_MAP[req.amount],
        "reference": reference,
        "metadata": {"user_id": user, "credits": req.amount}
    }

    try:
        res = requests.post("https://api.paystack.co/transaction/initialize", json=payload, headers=headers, timeout=15)
        data = res.json()

        if not data.get("status"):
            raise HTTPException(status_code=400, detail=data.get("message", "Paystack error"))

        return {
            "status": "success",
            "authorization_url": data["data"]["authorization_url"],
            "reference": reference
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail="Could not connect to Paystack")


@app.post("/paystack/webhook")
async def paystack_webhook(request: Request):
    if not PAYSTACK_SECRET_KEY:
        return {"status": "error"}

    body = await request.body()
    signature = request.headers.get("x-paystack-signature")

    expected = hmac.new(PAYSTACK_SECRET_KEY.encode(), body, hashlib.sha512).hexdigest()

    if not signature or signature != expected:
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload")

    if payload.get("event") != "charge.success":
        return {"status": "ignored"}

    data = payload.get("data", {})
    reference = data.get("reference")
    authorization = data.get("authorization", {})

    with sqlite3.connect("payments.db") as conn:
        row = conn.execute(
            "SELECT status, user_id, credits FROM payments WHERE reference=?", (reference,)
        ).fetchone()

        if not row or row[0] == "completed":
            return {"status": "ignored"}

        user_id = row[1]
        credits = row[2]

        conn.execute("UPDATE payments SET status='completed' WHERE reference=?", (reference,))
        conn.commit()

    # Save authorization code
    auth_code = authorization.get("authorization_code")
    last4 = authorization.get("last4")
    brand = authorization.get("brand") or authorization.get("card_type")

    if auth_code:
        with sqlite3.connect("users.db") as conn:
            conn.execute(
                """UPDATE users 
                   SET authorization_code = ?, last4 = ?, card_brand = ? 
                   WHERE username = ?""",
                (auth_code, last4, brand, user_id)
            )
            conn.commit()

    billing = runtime.get_agent("billing_agent")
    if billing:
        billing.add_credits(user_id, credits)

    return {"status": "success"}


# ────────────────────────────────────────────────
# AUTO RECHARGE (fixed URL)
# ────────────────────────────────────────────────
@app.post("/auto-recharge")
async def perform_auto_recharge(req: AutoRechargeRequest, user: str = Depends(get_current_user)):
    if not PAYSTACK_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Paystack not configured")

    with sqlite3.connect("users.db") as conn:
        row = conn.execute(
            "SELECT auto_recharge, authorization_code FROM users WHERE username=?",
            (user,)
        ).fetchone()

    if not row or row[0] != 1 or not row[1]:
        raise HTTPException(status_code=400, detail="Auto-recharge not enabled or no saved card")

    auth_code = row[1]
    amount_credits = req.amount
    amount_kobo = PRICE_MAP.get(amount_credits)

    if not amount_kobo:
        raise HTTPException(status_code=400, detail="Invalid amount")

    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}", "Content-Type": "application/json"}
    payload = {
        "authorization_code": auth_code,
        "email": get_safe_email(user),
        "amount": amount_kobo,
        "metadata": {"user_id": user, "credits": amount_credits, "source": "auto_recharge"}
    }

    try:
        res = requests.post("https://api.paystack.co/transaction/charge_authorization", 
                           json=payload, headers=headers, timeout=15)
        data = res.json()

        if data.get("status") and data["data"].get("status") in ["success", "processing"]:
            billing = runtime.get_agent("billing_agent")
            if billing:
                billing.add_credits(user, amount_credits)

            return {"status": "success", "message": f"Auto-recharged {amount_credits} credits"}
        else:
            raise HTTPException(status_code=400, detail=data.get("message", "Charge failed"))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Auto-recharge failed: {str(e)}")


# ────────────────────────────────────────────────
# STREAMING LOGS ENDPOINT (NEW)
# ────────────────────────────────────────────────
@app.get("/stream")
async def stream_logs():
    async def event_stream():
        last_index = 0

        while True:
            logs = getattr(runtime, "logs", [])

            if last_index < len(logs):
                for log in logs[last_index:]:
                    yield f"data: {log}\n\n"
                last_index = len(logs)

            await asyncio.sleep(0.5)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ────────────────────────────────────────────────
# CHAT & CREDITS
# ────────────────────────────────────────────────
@app.post("/chat")
async def chat(data: ChatRequest, user: str = Depends(get_current_user)):
    prompt = data.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    runtime.last_zip.pop(user, None)
    result = await engine.handle_prompt(prompt, user_id=user)

    zip_data = runtime.last_zip.get(user)
    encoded_zip = None
    if zip_data and zip_data.get("bytes"):
        encoded_zip = {
            "bytes": base64.b64encode(zip_data["bytes"]).decode("utf-8"),
            "filename": zip_data.get("filename", "nox_app.zip")
        }

    return {
        "response": result.get("response"),
        "zip": encoded_zip,
        "logs": result.get("logs", []),
        "graph": result.get("graph"),
    }


@app.get("/credits")
async def get_credits(user: str = Depends(get_current_user)):
    billing = runtime.get_agent("billing_agent")
    return billing.get_balance(user) if billing else {"credits": 0}

from fastapi.responses import FileResponse

@app.get("/download/latest")
async def download_latest(user: str = Depends(get_current_user)):
    # ─────────────────────────────
    # PRIMARY: get from runtime
    # ─────────────────────────────
    zip_data = getattr(runtime, "last_zip", {}).get(user)

    if zip_data and zip_data.get("path") and os.path.exists(zip_data["path"]):
        return FileResponse(
            path=zip_data["path"],
            filename=zip_data.get("filename", "nox_app.zip"),
            media_type="application/zip"
        )

    # ─────────────────────────────
    # FALLBACK: find latest ZIP on disk
    # ─────────────────────────────
    try:
        files = [
            f for f in os.listdir("generated_apps")
            if f.endswith(".zip")
        ]

        if files:
            # Sort by newest (based on filename timestamp or file modified time)
            files.sort(
                key=lambda x: os.path.getmtime(os.path.join("generated_apps", x)),
                reverse=True
            )

            latest_file = files[0]
            latest_path = os.path.join("generated_apps", latest_file)

            return FileResponse(
                path=latest_path,
                filename=latest_file,
                media_type="application/zip"
            )

    except Exception as e:
        print(f"[Download] Fallback error: {e}")

    # ─────────────────────────────
    # NOTHING FOUND
    # ─────────────────────────────
    raise HTTPException(status_code=404, detail="No build available")

@app.get("/builds")
async def get_builds(user: str = Depends(get_current_user)):
    try:
        with sqlite3.connect("builds.db") as conn:
            rows = conn.execute(
                """
                SELECT id, project_name, filename, created_at
                FROM builds
                WHERE user_id=?
                ORDER BY created_at DESC
                LIMIT 20
                """,
                (user,)
            ).fetchall()

        return {
            "builds": [
                {
                    "id": r[0],
                    "project_name": r[1],
                    "filename": r[2],
                    "created_at": r[3],
                }
                for r in rows
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{build_id}")
async def download_build(build_id: int, user: str = Depends(get_current_user)):
    try:
        with sqlite3.connect("builds.db") as conn:
            row = conn.execute(
                """
                SELECT path, filename FROM builds
                WHERE id=? AND user_id=?
                """,
                (build_id, user)
            ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Build not found")

        path, filename = row

        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="File missing")

        return FileResponse(
            path=path,
            filename=filename,
            media_type="application/zip"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/admin/dashboard")
async def admin_dashboard(user: str = Depends(require_admin)):
    try:
        # ───────────────── USERS ─────────────────
        with sqlite3.connect("users.db") as conn:
            users = conn.execute(
                "SELECT COUNT(*) FROM users"
            ).fetchone()[0]

        # ───────────────── REVENUE ─────────────────
        with sqlite3.connect("payments.db") as conn:
            revenue_total = conn.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM payments
                WHERE status = 'completed'
                """
            ).fetchone()[0]

            revenue_24h = conn.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM payments
                WHERE status = 'completed'
                AND created_at >= datetime('now','-1 day')
                """
            ).fetchone()[0]

        # ───────────────── CREDITS ─────────────────
        billing = runtime.get_agent("billing_agent")
        credits = 0

        if billing and hasattr(billing, "balances"):
            try:
                credits = sum(billing.balances.values())
            except Exception:
                credits = 0

        # ───────────────── RESPONSE ─────────────────
        return {
            "users": users,
            "credits": credits,
            "revenue_total": round(revenue_total / 100, 2),  # convert kobo → currency
            "revenue_24h": round(revenue_24h / 100, 2),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/forge-stats")
async def forge_stats():
    try:
        with sqlite3.connect("builds.db") as conn:
            total = conn.execute("SELECT COUNT(*) FROM builds").fetchone()[0]

            per_user = conn.execute("""
                SELECT user_id, COUNT(*) as count
                FROM builds
                GROUP BY user_id
                ORDER BY count DESC
                LIMIT 5
            """).fetchall()

        return {
            "apps_built": total,
            "top_users": [
                {"user": r[0], "count": r[1]} for r in per_user
            ]
        }

    except Exception as e:
        return {"error": str(e)}
    
@app.post("/admin/force-prompt")
async def force_prompt(data: dict):
    prompt = data.get("prompt", "")
    user = data.get("user", "admin")

    if not prompt:
        raise HTTPException(status_code=400, detail="Empty prompt")

    result = await engine.handle_prompt(prompt, user_id=user)

    return {"response": result.get("response")}    

@app.post("/admin/add-credits")
async def admin_add_credits(data: dict):
    user = data.get("user")
    amount = int(data.get("amount", 0))

    billing = runtime.get_agent("billing_agent")
    if not billing:
        raise HTTPException(status_code=500, detail="Billing not available")

    billing.add_credits(user, amount)

    return {"status": "ok", "user": user, "added": amount}           

@app.post("/admin/kill")
async def kill_system():
    runtime.logs.append("🔥 SYSTEM TERMINATED BY ADMIN")
    os._exit(0)

@app.post("/admin/replay-build")
async def replay_build(data: dict):
    build_id = data.get("id")

    with sqlite3.connect("builds.db") as conn:
        row = conn.execute(
            "SELECT project_name FROM builds WHERE id=?",
            (build_id,)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Build not found")

    prompt = f"Rebuild this project: {row[0]}"

    result = await engine.handle_prompt(prompt, user_id="admin")

    return {"response": result.get("response")}

@app.get("/")
async def root():
    return {"status": "ok", "message": "NOX backend running"}

# Optional: Add more admin endpoints
@app.get("/forge-stats")
async def forge_stats():
    return {
        "total_builds": 0,   # count from db
        "success_rate": 100,
        "recent_activity": []
    }    

    