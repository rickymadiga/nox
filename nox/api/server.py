import os
import io
import asyncio
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

# NOX Engine
from nox.runtime.engine_runtime import engine

# ────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────
load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"

security = HTTPBearer()

# ────────────────────────────────────────────────
# GLOBAL RUNTIME & MULTI-USER ZIP STORAGE
# ────────────────────────────────────────────────
runtime = engine.runtime

# Safe initialization of multi-user zip storage
if not hasattr(runtime, "last_zip") or not isinstance(runtime.last_zip, dict):
    runtime.last_zip = {}

# ────────────────────────────────────────────────
# IN-MEMORY DATABASE (TEMPORARY)
# ────────────────────────────────────────────────
users_db: dict[str, dict] = {}

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
        algorithm=ALGORITHM,
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
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ────────────────────────────────────────────────
# LIFESPAN
# ────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 NOX Backend starting...")
    # Plugins are loaded inside Engine.__init__ — no need to reload here
    yield
    print("🛑 NOX Backend shutting down...")


# ────────────────────────────────────────────────
# FASTAPI APP SETUP
# ────────────────────────────────────────────────
app = FastAPI(title="NOX AI Backend", lifespan=lifespan)

# Static exports
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
# HEALTH CHECK
# ────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"status": "running", "service": "NOX AI"}


# ────────────────────────────────────────────────
# DOWNLOAD ENDPOINTS
# ────────────────────────────────────────────────
@app.get("/download/latest")
async def download_latest(user: str = Depends(get_current_user)):
    """Download the latest generated project for the current user."""
    user_zip = runtime.last_zip.get(user)

    if not user_zip or "bytes" not in user_zip:
        raise HTTPException(status_code=404, detail="No project found for this user")

    return StreamingResponse(
        io.BytesIO(user_zip["bytes"]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={user_zip.get('filename', 'project.zip')}"
        }
    )


@app.get("/download/{project}")
async def download_project(project: str):
    """Download a specific exported project."""
    path = f"generated_apps/{project}.zip"

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Project not found")

    return FileResponse(
        path,
        media_type="application/zip",
        filename=f"{project}.zip"
    )


# ────────────────────────────────────────────────
# AUTHENTICATION
# ────────────────────────────────────────────────
@app.post("/signup")
async def signup(data: AuthRequest):
    if data.username in users_db:
        raise HTTPException(status_code=400, detail="User already exists")

    users_db[data.username] = {
        "password": data.password,
        "credits": 50,
        "auto_recharge": False
    }

    return {"message": "User created successfully"}


@app.post("/login")
async def login(data: AuthRequest):
    user = users_db.get(data.username)

    if not user or user.get("password") != data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"token": create_token(data.username)}


# ────────────────────────────────────────────────
# CHAT ENDPOINT (Main Brain → Engine Flow)
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

        # Ensure zip storage exists
        if not hasattr(runtime, "last_zip") or runtime.last_zip is None:
            runtime.last_zip = {}

        print(f"[CHAT] Processing prompt for user={user}")

        # Run through Engine (Lily decides action → delegate or respond)
        result = await engine.handle_prompt(prompt, user_id=user)

        # Extract safely
        response_text = result.get("response") or result.get("message") or str(result)
        logs = result.get("logs", [])
        graph = result.get("graph") or result.get("execution_graph")

        # Get user-specific ZIP
        user_zip = runtime.last_zip.get(user) if isinstance(runtime.last_zip, dict) else None

        # Build final response
        chat_response = {
            "status": "success",
            "response": response_text,
            "logs": logs,
            "zip_ready": bool(user_zip),
            "filename": user_zip.get("filename") if user_zip else None,
        }

        # Attach full ZIP when available (for frontend download)
        if user_zip:
            chat_response["zip"] = user_zip

        # Attach graph for frontend visualization
        if graph:
            chat_response["graph"] = graph

        print(f"[DEBUG] ZIP READY for {user}: {bool(user_zip)}")

        return chat_response

    except Exception as e:
        print(f"[CHAT ERROR] {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ────────────────────────────────────────────────
# STREAMING LOGS
# ────────────────────────────────────────────────
@app.get("/stream")
async def stream(user: str = Depends(get_current_user)):
    agent = runtime.get_agent("code_agent")

    if not agent:
        async def empty_stream():
            yield "data: No code_agent available\n\n"
        return StreamingResponse(empty_stream(), media_type="text/event-stream")

    async def generator():
        async for msg in agent.stream(user):
            yield f"data: {msg}\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")


# ────────────────────────────────────────────────
# CREDITS
# ────────────────────────────────────────────────
@app.get("/credits")
async def get_credits(user: str = Depends(get_current_user)):
    user_data = users_db.get(user, {})
    return {"credits": user_data.get("credits", 0)}


# ────────────────────────────────────────────────
# AUTO RECHARGE (Placeholder)
# ────────────────────────────────────────────────
@app.post("/toggle-auto-recharge")
async def toggle_auto_recharge(req: AutoRechargeRequest, user: str = Depends(get_current_user)):
    if user not in users_db:
        raise HTTPException(status_code=404, detail="User not found")

    users_db[user]["auto_recharge"] = req.enabled

    return {
        "status": "ok",
        "auto_recharge": req.enabled,
        "message": f"Auto-recharge {'enabled' if req.enabled else 'disabled'}"
    }