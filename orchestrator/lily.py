# lily.py — NOX GOD BRAIN v14 (Smarter Context-Aware Assistant)

import time
import random
from typing import Dict, Any, List

from orchestrator.memory import Memory


class Lily:
    def __init__(self, user_name: str = "NOX"):
        self.user_name = user_name
        self.memory = Memory()

        self.system_state = {
            "active_jobs": {},
            "pending_quotes": {},
            "conversation_history": {}   # New: better memory
        }

        self.runtime = None
        self.step = 0

    def attach_runtime(self, runtime):
        self.runtime = runtime
        runtime.bus.subscribe("forge_complete", self.on_forge_complete)
        print("🔥 LILY v14 SMARTER CONTEXT-AWARE MODE LOADED 🚀")

    async def on_forge_complete(self, message):
        payload = message.payload if hasattr(message, "payload") else message.get("payload", {})
        user_id = payload.get("user_id", "default_user")
        self.memory.set_user_value(user_id, "last_build", payload)

        # Store in conversation history too
        if user_id not in self.system_state["conversation_history"]:
            self.system_state["conversation_history"][user_id] = []
        self.system_state["conversation_history"][user_id].append({"role": "system", "content": "Build completed successfully"})

    # ────────────────────────────────────────────────
    # IMPROVED INTENT DETECTION
    # ────────────────────────────────────────────────
    def classify_intent(self, text: str, user_id: str = None) -> str:
        t = text.lower().strip()

        # Strong confirmation
        confirm_words = ["yes", "yeah", "yep", "sure", "go ahead", "proceed", "do it", "let's go", "confirm", "ok", "alright"]
        if any(x in t for x in confirm_words) and user_id in self.system_state["pending_quotes"]:
            return "confirm"

        # Build / create intent
        build_phrases = ["build", "create", "make", "develop", "code", "generate", "i want", "can you build", "make me", "i need an app"]
        if any(x in t for x in build_phrases):
            return "build"

        # Refinement / follow-up
        if user_id in self.system_state["pending_quotes"] and any(word in t for word in ["change", "modify", "add", "remove", "instead", "but", "actually"]):
            return "refine"

        return "chat"

    # ────────────────────────────────────────────────
    # BETTER BUILD PLANNING
    # ────────────────────────────────────────────────
    def plan_build(self, prompt: str) -> List[str]:
        steps = ["Planner"]
        p = prompt.lower()

        if any(x in p for x in ["api", "backend", "server"]): steps.append("API Designer")
        if any(x in p for x in ["ai", "chatbot", "llm", "gpt"]): steps.append("AI Module")
        if any(x in p for x in ["payment", "pay", "stripe", "paystack"]): steps.append("Billing Integration")
        if any(x in p for x in ["auth", "login", "register", "user"]): steps.append("Auth System")
        if any(x in p for x in ["dashboard", "admin"]): steps.append("Dashboard")
        if "mobile" in p or "android" in p or "ios" in p: steps.append("Mobile UI")

        steps += ["Coder", "Tester", "Reviewer", "Assembler"]
        return steps

    # ────────────────────────────────────────────────
    # IMPROVED PRICING ENGINE
    # ────────────────────────────────────────────────
    def estimate_price(self, prompt: str, context: dict) -> int:
        p = prompt.lower()
        price = 180  # slightly lowered base

        # Feature detection
        if any(x in p for x in ["api", "backend", "server", "database"]): price += 90
        if any(x in p for x in ["ai", "chatbot", "llm", "intelligence"]): price += 130
        if any(x in p for x in ["payment", "paystack", "stripe", "checkout"]): price += 110
        if any(x in p for x in ["auth", "login", "signup", "user account"]): price += 75
        if any(x in p for x in ["dashboard", "admin panel"]): price += 65
        if "mobile" in p: price += 80

        # Complexity
        word_count = len(p.split())
        if word_count > 15: price += 60
        if word_count > 30: price += 90

        if any(x in p for x in ["full", "complete", "production", "deploy", "live"]): price += 140

        if context.get("web_results"): price += 40

        return max(180, price)

    def negotiate_price(self, user_input: str, price: int) -> int:
        t = user_input.lower()
        if any(word in t for word in ["expensive", "reduce", "cheaper", "discount", "less"]):
            return max(150, int(price * 0.88))
        if any(word in t for word in ["cheap", "too much"]):
            return max(150, int(price * 0.82))
        return price

    # ────────────────────────────────────────────────
    # WEB ENRICHMENT
    # ────────────────────────────────────────────────
    async def maybe_use_web(self, prompt: str, user_id: str, context: dict):
        needs_web = any(word in prompt.lower() for word in ["latest", "best", "trend", "current", "2026", "2025"])
        if not needs_web or not self.runtime:
            return context

        web = self.runtime.get_agent("web_agent")
        if web:
            try:
                web_data = await web.run({"query": prompt, "user_id": user_id})
                context["web_results"] = web_data.get("results", [])
            except Exception as e:
                print("[WEB ERROR]", e)
        return context

    # ────────────────────────────────────────────────
    # MESSAGE HELPERS (Improved)
    # ────────────────────────────────────────────────
    def get_low_credits_message(self, available: int) -> str:
        options = [
            f"I'd really like to build this for you, but you're currently low on credits (only {available} left). "
            f"You'll need at least 200 credits to start. Would you like to recharge now?",
            
            f"This is a great idea! Unfortunately we need more credits to begin ({available} available). "
            f"Recharge and I'll start working on it right away.",
            
            f"I'm excited about this project, but credits are currently at {available}. "
            f"Top up whenever you're ready and we'll bring your idea to life."
        ]
        return random.choice(options)

    def get_quote_message(self, price: int, steps: List[str]) -> str:
        step_str = " → ".join(steps)
        return (
            f"This build will cost **{price} credits**.\n\n"
            f"Planned steps: {step_str}\n\n"
            f"Ready to proceed? Just reply with **yes** and I'll start building it for you."
        )

    def get_build_started_message(self, price: int) -> str:
        return f"Starting your build now using {price} credits. I'll work on it and keep you updated as it progresses."

    # ────────────────────────────────────────────────
    # SMARTER CHAT RESPONSES (Big Upgrade)
    # ────────────────────────────────────────────────
    def get_smart_chat_response(self, user_input: str, user_id: str) -> str:
        last_build = self.memory.get_user_value(user_id, "last_build")
        history = self.system_state["conversation_history"].get(user_id, [])

        t = user_input.lower()

        if any(greet in t for greet in ["hi", "hello", "hey", "sup", "greetings"]):
            if last_build:
                return "Great to see you again! We built something nice last time. What would you like to create or improve today?"
            return "Hello! I'm here to help you build amazing apps and tools. What's your idea today?"

        if any(word in t for word in ["how are you", "how r u", "how's it going"]):
            return "I'm doing well and ready to help you build something great. How can I assist you today?"

        if "idea" in t or "thought" in t or "concept" in t:
            return "Awesome! Please share your idea in as much detail as you'd like. The more specific you are, the better I can help bring it to life."

        if "help" in t or "can you" in t or "what can you" in t:
            return "Of course! I can help you build web apps, mobile apps, AI tools, dashboards, APIs, and more. Just describe what you need."

        # Follow-up / refinement detection
        if last_build and any(word in t for word in ["improve", "add", "change", "update", "next", "another"]):
            return "I'd be happy to help refine or build upon your previous project. What would you like to add or change?"

        # Default smart responses
        responses = [
            "I'm ready to help you build something useful. Could you tell me more about the app or tool you have in mind?",
            "That sounds interesting! Feel free to describe the features you'd like in your app.",
            "I'm here to turn your ideas into working applications. What's the main goal of this project?",
            "Let's create something great together. What kind of functionality are you looking for?"
        ]
        return random.choice(responses)

    # ────────────────────────────────────────────────
    # MAIN ENTRY POINT
    # ────────────────────────────────────────────────
    async def run(self, task: Dict[str, Any]):
        user_input = str(task.get("prompt") or "")
        user_id = task.get("user_id", "default_user")
        context = task.get("context", {})

        self.step += 1
        intent = self.classify_intent(user_input, user_id)

        # Initialize conversation history
        if user_id not in self.system_state["conversation_history"]:
            self.system_state["conversation_history"][user_id] = []
        self.system_state["conversation_history"][user_id].append({"role": "user", "content": user_input})

        # Expire old quotes
        quote = self.system_state["pending_quotes"].get(user_id)
        if quote and time.time() - quote.get("created_at", 0) > 300:
            self.system_state["pending_quotes"].pop(user_id, None)
            quote = None

        # Negotiation / Refinement
        if quote and intent == "refine":
            new_price = self.negotiate_price(user_input, quote["price"])
            if new_price != quote["price"]:
                quote["price"] = new_price
                return {
                    "action": "quote",
                    "price": new_price,
                    "message": f"I've adjusted the estimated cost to **{new_price} credits** based on your feedback. Does this work for you? Just say yes to proceed."
                }

        # LOW CREDITS CHECK
        if intent in ["build", "confirm"]:
            billing = self.runtime.get_agent("billing_agent") if self.runtime else None
            if billing:
                balance = billing.get_balance(user_id)
                available = balance.get("available", 0)
                if available < 200:
                    return {
                        "action": "respond",
                        "message": self.get_low_credits_message(available)
                    }

        # Confirm build
        if intent == "confirm":
            if not quote:
                return {
                    "action": "respond",
                    "message": "I don't have an active quote at the moment. Please describe what you'd like me to build."
                }

            self.system_state["pending_quotes"].pop(user_id, None)
            return {
                "action": "build",
                "price": quote["price"],
                "prompt": quote["prompt"],
                "context": quote["context"],
                "message": self.get_build_started_message(quote["price"])
            }

        # Build request
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
                "message": self.get_quote_message(price, steps)
            }

        # Default smart chat
        response = self.get_smart_chat_response(user_input, user_id)
        self.system_state["conversation_history"][user_id].append({"role": "assistant", "content": response})

        return {
            "action": "respond",
            "message": response
        }


# ────────────────────────────────────────────────
# REGISTER
# ────────────────────────────────────────────────
def register(runtime):
    lily = Lily()
    runtime.register_agent("lily", lily)
    lily.attach_runtime(runtime)
    print("[PLUGIN] Lily v14 Smarter Context-Aware Mode Loaded 🚀")