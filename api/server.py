import stripe
import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from nox.runtime.engine_runtime import Runtime, engine
from nox.runtime.plugin_loader import load_plugins

# ────────────────────────────────────────────────
# CONFIG & STATIC EXPORTS SETUP
# ────────────────────────────────────────────────
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# ✅ Ensure exports folder exists
os.makedirs("exports", exist_ok=True)

app = FastAPI(title="NOX AI Backend")

# Mount static exports folder
app.mount("/exports", StaticFiles(directory="exports"), name="exports")

# ────────────────────────────────────────────────
# RUNTIME
# ────────────────────────────────────────────────
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
# REQUEST MODELS
# ────────────────────────────────────────────────
class AutoRechargeRequest(BaseModel):
    user_id: str
    enabled: bool


# ────────────────────────────────────────────────
# ROOT
# ────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "service": "NOX AI Backend",
        "status": "running",
        "version": "1.2"
    }


# ────────────────────────────────────────────────
# CHAT
# ────────────────────────────────────────────────
@app.post("/chat")
async def chat(data: dict):
    prompt = data.get("prompt", "")
    user_id = data.get("user_id", "default_user")

    result = await engine.handle_prompt(prompt, user_id=user_id)
    print("ENGINE RESULT:", result)
    return result


# ────────────────────────────────────────────────
# LOGS & LIVE STREAM
# ────────────────────────────────────────────────
@app.get("/logs/{user_id}")
async def get_logs(user_id: str):
    code_agent = runtime.get_agent("code_agent")
    if not code_agent:
        return {"logs": []}

    try:
        logs = await code_agent.run({"user_id": user_id})
        return {"logs": logs}
    except Exception as e:
        print(f"[Logs] Error: {e}")
        return {"logs": []}


@app.get("/stream/{user_id}")
async def stream_logs(user_id: str):
    code_agent = runtime.get_agent("code_agent")
    if not code_agent:
        async def empty_generator():
            yield "data: [ERROR] Code agent not available\n\n"
        return StreamingResponse(empty_generator(), media_type="text/event-stream")

    async def event_generator():
        try:
            async for message in code_agent.stream(user_id):
                if isinstance(message, dict):
                    message = str(message.get("message", message))
                yield f"data: {message}\n\n"
        except Exception as e:
            print(f"[Stream] Error: {e}")
            yield f"data: [ERROR] Stream issue: {str(e)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


# ────────────────────────────────────────────────
# CREDITS
# ────────────────────────────────────────────────
@app.get("/credits/{user_id}")
async def get_credits(user_id: str):
    billing = runtime.get_agent("billing_agent")
    if not billing:
        return {"credits": 0, "plan": "free", "is_admin": False}

    try:
        user = billing._get_user(user_id)
        return {
            "credits": user.get("credits", 0),
            "plan": user.get("plan", "free"),
            "is_admin": user.get("is_admin", False)
        }
    except Exception as e:
        print(f"[Credits] Error: {e}")
        return {"credits": 0, "plan": "free", "is_admin": False}


# ────────────────────────────────────────────────
# CREATE CHECKOUT SESSION - FIXED VERSION
# ────────────────────────────────────────────────
@app.post("/create-checkout-session")
async def create_checkout(payload: dict):
    """Create Stripe checkout session - Direct implementation"""
    try:
        user_id = payload.get("user_id")
        plan = payload.get("plan")

        if not user_id or not plan:
            raise HTTPException(status_code=400, detail="Missing user_id or plan")

        price_map = {
            "starter": 500,   # $5.00
            "pro":     2000,  # $20.00
            "mega":    5000   # $50.00
        }

        unit_amount = price_map.get(plan.lower())
        if unit_amount is None:
            raise HTTPException(status_code=400, detail=f"Invalid plan: {plan}")

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"{plan.capitalize()} Credits"},
                    "unit_amount": unit_amount,
                },
                "quantity": 1,
            }],
            success_url="http://localhost:8501?success=true",
            cancel_url="http://localhost:8501?cancel=true",
            metadata={"user_id": user_id, "plan": plan}
        )

        return {"url": session.url}

    except stripe.error.StripeError as e:
        print("🔥 Stripe Error:", str(e))
        return JSONResponse(status_code=400, content={"error": f"Stripe: {str(e)}"})
    except HTTPException as e:
        raise e
    except Exception as e:
        print("🔥 Checkout Error:", str(e))
        return JSONResponse(status_code=500, content={"error": str(e)})


# ────────────────────────────────────────────────
# STRIPE WEBHOOK
# ────────────────────────────────────────────────
@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    stripe_agent = runtime.get_agent("stripe_agent")
    billing = runtime.get_agent("billing_agent")

    if not stripe_agent or not billing:
        return JSONResponse({"status": "missing agents"}, status_code=400)

    result = stripe_agent.handle_webhook(payload, sig_header)

    if result.get("action") == "add_credits":
        billing.add_credits(result.get("user_id"), result.get("credits", 0))

    elif result.get("action") == "auto_topup":
        user_id = stripe_agent.get_user_from_customer(result.get("customer_id"))
        if user_id:
            billing.add_credits(user_id, result.get("credits", 100))

    return JSONResponse({"status": "ok"})


# ────────────────────────────────────────────────
# AUTO RECHARGE
# ────────────────────────────────────────────────
@app.post("/toggle-auto-recharge")
async def toggle_auto_recharge(req: AutoRechargeRequest):
    billing = runtime.get_agent("billing_agent")
    if not billing:
        return {"status": "error", "message": "Billing agent not available"}

    try:
        billing.set_auto_recharge(req.user_id, req.enabled)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ────────────────────────────────────────────────
# ADMIN ROUTES
# ────────────────────────────────────────────────
@app.get("/admin/dashboard")
async def admin_dashboard():
    admin = runtime.get_agent("admin_agent")
    if not admin:
        return {"error": "Admin agent not available"}
    return admin.get_dashboard()

# ... (keep all your other admin routes as they are)
@app.get("/admin/users")
async def admin_users():
    admin = runtime.get_agent("admin_agent")
    if not admin: return {"error": "Admin agent not available"}
    return {"users": admin.get_all_users()}

@app.get("/admin/transactions")
async def admin_transactions():
    admin = runtime.get_agent("admin_agent")
    if not admin: return {"error": "Admin agent not available"}
    return admin.get_transactions()

@app.post("/admin/add-credits")
async def admin_add_credits(data: dict):
    admin = runtime.get_agent("admin_agent")
    billing = runtime.get_agent("billing_agent")
    if not admin or not billing:
        return {"status": "error", "message": "Required agents not available"}
    admin.add_credits(billing, data.get("user_id"), data.get("amount"))
    return {"status": "ok"}

# (Keep the rest of your admin routes unchanged: revenue, mrr, tickets, etc.)

# ────────────────────────────────────────────────
# STARTUP
# ────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    print("🚀 NOX Backend started successfully")
    print(f"Stripe configured: {'Yes' if stripe.api_key else 'No'}")