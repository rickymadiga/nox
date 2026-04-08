from nox.core.agent import Agent
from nox.core.message import Message
import random
import time


class ForgeWatcher(Agent):
    """
    Cinematic AI Narrator for NOX ✨
    Transforms system events into elegant, human-like live storytelling
    """

    def __init__(self, runtime):
        self.runtime = runtime
        self.bus = runtime.bus
        self.name = "forge_watcher"

        # ✨ Elegant Personality Library
        self.personality = {
            "TASK_REQUEST": [
                "🌟 A new vision has been received...",
                "🧠 The creative process begins. Analyzing the request...",
                "✨ Someone wants to build something beautiful. Let's begin.",
            ],
            "PLAN_CREATED": [
                "📐 Crafting a thoughtful system architecture...",
                "🧩 Designing clean, logical foundations...",
                "🌱 Planting the seeds of a well-structured application...",
            ],
            "CODE_GENERATED": [
                "💻 Weaving elegant code into existence...",
                "🔨 Bringing the blueprint to life with precision...",
                "✍️ Writing thoughtful, maintainable logic...",
            ],
            "TEST_RESULTS": [
                "🧪 Running careful validations across the system...",
                "🔍 Ensuring everything behaves as intended...",
                "⚖️ Testing for strength and reliability...",
            ],
            "REVIEW_COMPLETED": [
                "🔎 Performing a thoughtful code review...",
                "✨ Polishing edges and refining details...",
                "🌟 Elevating the quality with care...",
            ],
            "CODE_APPROVED": [
                "✅ All systems aligned. The foundation is solid.",
                "🌟 Code passes with grace and clarity.",
                "🎉 Beautiful work. Ready for the final stage.",
            ],
            "build_started": [
                "🚀 The forge has been lit. Beginning construction...",
                "🌟 Starting the build journey with focus and care...",
                "🔥 The creative engine is now running.",
            ],
            "build_complete": [
                "✨ The build is complete. A new creation has been born.",
                "🌟 Your application is ready. Delivered with care.",
                "🎉 The forge rests. Another beautiful piece finished.",
            ],
            "build_failed": [
                "⚠️ The process encountered an obstacle.",
                "🌧️ Something interrupted the flow. Investigating...",
                "🛠️ A step needs attention before we continue.",
            ],
            "forge_complete": [
                "🌟 The journey is complete. Your app is ready to shine.",
                "✨ With care and precision, the build has been fulfilled.",
                "🎨 A new digital creation stands finished.",
            ]
        }

        # Subscribe to all relevant events
        for event_type in self.personality.keys():
            self.bus.subscribe(event_type, self.on_event)

        print(f"[{self.name}] ✨ Cinematic Narrator initialized")

    # ─────────────────────────────────────────────
    async def on_event(self, message: Message):
        try:
            event_type = getattr(message, "message_type", None)
            if not event_type:
                return

            payload = getattr(message, "payload", {}) or {}

            # Choose elegant base line
            lines = self.personality.get(event_type, [f"📍 {event_type.replace('_', ' ').title()}"])
            base_line = random.choice(lines)

            # Add rich context when available
            user_prompt = payload.get("prompt") or payload.get("task")
            if user_prompt and len(str(user_prompt)) > 5:
                base_line += f"\n   ↳ Vision: {str(user_prompt)[:80]}{'...' if len(str(user_prompt)) > 80 else ''}"

            if status := payload.get("status"):
                base_line += f" — {status}"

            if cost := payload.get("cost"):
                base_line += f" • {cost} credits invested"

            if error := payload.get("error"):
                base_line += f"\n   ⚠️  {error}"

            # Add to runtime logs (for streaming)
            if not hasattr(self.runtime, "logs") or self.runtime.logs is None:
                self.runtime.logs = []

            timestamp = time.strftime("%H:%M:%S")
            formatted_log = f"[{timestamp}] {base_line}"

            self.runtime.logs.append(formatted_log)

            # Keep only last 150 logs
            if len(self.runtime.logs) > 150:
                self.runtime.logs = self.runtime.logs[-150:]

            # Console output (clean & beautiful)
            print(f"✨ [ForgeWatcher] {base_line}")

        except Exception as e:
            print(f"[ForgeWatcher] Error processing event: {e}")

    # ─────────────────────────────────────────────
    def run(self, task: dict):
        """Keep alive message"""
        return {
            "message": "✨ ForgeWatcher is quietly observing and narrating the creative process...",
            "status": "active",
            "agent": self.name
        }


# ─────────────────────────────────────────────
# PLUGIN ENTRY POINT
# ─────────────────────────────────────────────
def register(runtime):
    agent = ForgeWatcher(runtime)
    runtime.register_agent("forge_watcher", agent)
    print("[PLUGIN] ✨ ForgeWatcher — Cinematic Narrator Loaded")