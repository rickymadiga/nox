import stripe
import os

from dotenv import load_dotenv
load_dotenv()

from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.routes.build import router as build_router
from nox.runtime.engine_runtime import engine  # ✅ USE ENGINE ONLY


# ────────────────────────────────────────────────
# STRIPE CONFIG
# ────────────────────────────────────────────────
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

BASE_URL = os.getenv("BASE_URL", "http://localhost:8501")


# ────────────────────────────────────────────────
# REQUEST MODEL
# ────────────────────────────────────────────────
class PromptRequest(BaseModel):
    prompt: str


# ────────────────────────────────────────────────
# APP INIT
# ────────────────────────────────────────────────
app = FastAPI(title="Forge AI Builder")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(build_router)


# ────────────────────────────────────────────────
# HEALTH CHECK
# ────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "service": "Forge AI Builder",
        "status": "running"
    }


# ────────────────────────────────────────────────
# MAIN CHAT (USES ENGINE)
# ────────────────────────────────────────────────
@app.post("/chat")
async def chat(data: dict):
    prompt = data.get("prompt", "")

    result = await engine.handle_prompt(prompt)

    print("ENGINE RESULT:", result)

    return result


# ────────────────────────────────────────────────
# STRIPE CHECKOUT SESSION
# ────────────────────────────────────────────────
@app.post("/create-checkout-session")
async def create_checkout(request: Request):
    data = await request.json()

    user_id = data.get("user_id", "default_user")
    plan = data.get("plan")

    stripe_agent = engine.runtime.get_agent("stripe_agent")

    if not stripe_agent:
        return {"error": "Stripe agent not available"}

    result = stripe_agent.run({
        "action": "checkout",
        "user_id": user_id,
        "plan": plan
    })

    return result


# ────────────────────────────────────────────────
# STRIPE WEBHOOK (REAL MONEY HANDLER)
# ────────────────────────────────────────────────
@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            webhook_secret
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    # ─────────────────────────────
    # PAYMENT SUCCESS
    # ─────────────────────────────
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        user_id = session["metadata"]["user_id"]
        plan = session["metadata"]["plan"]

        billing = engine.runtime.get_agent("billing_agent")

        if not billing:
            return {"error": "Billing agent not found"}

        # 🔥 CREDIT PACKS
        credits_map = {
            "starter": 50,
            "pro": 250,
            "mega": 1000
        }

        credits = credits_map.get(plan, 50)

        # 🔥 UPDATE USER BALANCE
        user = billing._get_user(user_id)
        new_credits = user["credits"] + credits
        billing._update_credits(user_id, new_credits)

        print(f"[STRIPE] {user_id} +{credits} credits")

    return {"status": "success"}


# ────────────────────────────────────────────────
# LEGACY PROMPT (OPTIONAL)
# ────────────────────────────────────────────────
@app.post("/prompt")
async def handle_prompt(req: PromptRequest):
    result = await engine.handle_prompt(req.prompt)
    return result