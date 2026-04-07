# lily.py — NOX GOD BRAIN v11 (SMART PRICING + CLEAN FLOW)

import time
from typing import Dict, Any, List

from orchestrator.memory import Memory


class Lily:
    def __init__(self, user_name: str = "NOX"):
        self.user_name = user_name
        self.memory = Memory()

        self.system_state = {
            "active_jobs": {},
            "pending_quotes": {}
        }

        self.runtime = None
        self.step = 0

    # ────────────────────────────────────────────────
    # CONNECT TO RUNTIME
    # ────────────────────────────────────────────────
    def attach_runtime(self, runtime):
        self.runtime = runtime
        runtime.bus.subscribe("forge_complete", self.on_forge_complete)
        print("🔥 LILY V11 LOADED")

    async def on_forge_complete(self, message):
        payload = message.payload if hasattr(message, "payload") else message.get("payload", {})
        user_id = payload.get("user_id", "default_user")

        self.memory.set_user_value(user_id, "last_build", payload)

        job = self.system_state["active_jobs"].get(user_id)
        if job:
            job["status"] = "completed"
            job["result"] = payload

    # ────────────────────────────────────────────────
    # INTENT DETECTION
    # ────────────────────────────────────────────────
    def classify_intent(self, text: str, user_id: str = None) -> str:
        t = text.lower().strip()

        confirm_words = ["yes", "y", "confirm", "ok", "go ahead", "proceed", "build it"]
        build_words = ["build", "create", "make", "generate"]

        if any(x in t for x in confirm_words):
            if user_id in self.system_state["pending_quotes"]:
                return "confirm"

        if any(x in t for x in build_words):
            return "build"

        return "chat"

    # ────────────────────────────────────────────────
    # BUILD PLANNING
    # ────────────────────────────────────────────────
    def plan_build(self, prompt: str) -> List[str]:
        steps = ["Planner"]
        p = prompt.lower()

        if "api" in p:
            steps.append("API Designer")

        if "ai" in p or "chatbot" in p:
            steps.append("AI Module")

        if "payment" in p:
            steps.append("Billing Integration")

        if "auth" in p or "login" in p:
            steps.append("Auth System")

        steps += ["Coder", "Tester", "Reviewer", "Assembler"]

        return steps

    # ────────────────────────────────────────────────
    # SMART PRICING ENGINE
    # ────────────────────────────────────────────────
    def estimate_price(self, prompt: str, context: dict) -> int:
        p = prompt.lower()

        # Base price (serious builders only)
        price = 200

        # Feature-based pricing
        if "api" in p:
            price += 80

        if "ai" in p or "chatbot" in p:
            price += 120

        if "payment" in p:
            price += 100

        if "auth" in p or "login" in p:
            price += 70

        if "dashboard" in p:
            price += 60

        # Complexity scaling
        if len(p.split()) > 10:
            price += 50

        if len(p.split()) > 20:
            price += 100

        # Full production apps
        if any(x in p for x in ["full", "complete", "production", "deploy"]):
            price += 150

        # Web-enhanced builds cost more
        if context.get("web_results"):
            price += 50

        return max(200, price)

    # ────────────────────────────────────────────────
    # NEGOTIATION SYSTEM
    # ────────────────────────────────────────────────
    def negotiate_price(self, user_input: str, price: int) -> int:
        t = user_input.lower()

        if "too expensive" in t or "reduce" in t:
            return int(price * 0.9)

        if "cheap" in t:
            return int(price * 0.85)

        return price

    # ────────────────────────────────────────────────
    # WEB ENRICHMENT (OPTIONAL)
    # ────────────────────────────────────────────────
    async def maybe_use_web(self, prompt: str, user_id: str, context: dict):
        needs_web = any(word in prompt.lower() for word in ["latest", "best", "trend", "api", "2026"])

        if not needs_web or not self.runtime:
            return context

        web = self.runtime.get_agent("web_agent")
        if not web:
            return context

        try:
            web_data = await web.run({
                "query": prompt,
                "user_id": user_id
            })

            results = web_data.get("results", [])
            context["web_results"] = results

        except Exception as e:
            print("[WEB ERROR]", e)

        return context

    # ────────────────────────────────────────────────
    # MAIN ENTRY
    # ────────────────────────────────────────────────
    async def run(self, task: Dict[str, Any]):
        user_input = str(task.get("prompt") or "")
        user_id = task.get("user_id", "default_user")
        context = task.get("context", {})

        self.step += 1
        print(f"[LILY v11] Step {self.step} → {user_input}")

        intent = self.classify_intent(user_input, user_id)

        # Expire old quotes
        quote = self.system_state["pending_quotes"].get(user_id)
        if quote and time.time() - quote.get("created_at", 0) > 300:
            self.system_state["pending_quotes"].pop(user_id, None)
            quote = None

        # NEGOTIATION
        if quote:
            new_price = self.negotiate_price(user_input, quote["price"])
            if new_price != quote["price"]:
                quote["price"] = new_price
                return {
                    "action": "quote",
                    "price": new_price,
                    "message": f"💰 Updated price: {new_price} credits. Say 'yes' to proceed."
                }

        # 🔥 LOW BALANCE CHECK - BEFORE ANY BUILD
        if intent == "build" or intent == "confirm":
            billing = self.runtime.get_agent("billing_agent") if self.runtime else None
            if billing:
                balance = billing.get_balance(user_id)
                if balance.get("credits", 0) < 200:
                    return {
                        "action": "respond",
                        "message": "⚠️ You need at least 200 credits to start a build."
                    }

        # CONFIRM BUILD
        if intent == "confirm":
            if not quote:
                return {
                    "action": "respond",
                    "message": "❌ No active quote. Ask me to build something first."
                }

            self.system_state["pending_quotes"].pop(user_id, None)

            return {
                "action": "build",
                "price": quote["price"],
                "prompt": quote["prompt"],
                "context": quote["context"],
                "message": f"🚀 Building started ({quote['price']} credits)..."
            }

        # BUILD REQUEST → ALWAYS QUOTE FIRST
        if intent == "build":
            context = await self.maybe_use_web(user_input, user_id, context)

            price = self.estimate_price(user_input, context)
            steps = self.plan_build(user_input)

            self.system_state["pending_quotes"][user_id] = {
                "price": price,
                "prompt": user_input,
                "context": context,
                "steps": steps,
                "created_at": time.time()
            }

            return {
                "action": "quote",
                "price": price,
                "message": f"💰 Cost: {price} credits\n🧠 Plan: {' → '.join(steps)}\n\nType 'yes' to proceed."
            }

        # DEFAULT CHAT
        return {
            "action": "respond",
            "message": "Tell me what you'd like to build 🚀"
        }
# ────────────────────────────────────────────────
# REGISTER
# ────────────────────────────────────────────────
def register(runtime):
    lily = Lily()
    runtime.register_agent("lily", lily)
    lily.attach_runtime(runtime)
    print("[PLUGIN] Lily v11 Smart Pricing 🚀")