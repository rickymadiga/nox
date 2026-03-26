import time
import random


class MonetizationAgent:
    def __init__(self):
        self.user_behavior = {}  # simple memory
        self.last_pitch_time = {}

    # =========================================================
    # TRACK USER BEHAVIOR
    # =========================================================
    def track(self, user_id, action, success=True):
        if user_id not in self.user_behavior:
            self.user_behavior[user_id] = {
                "build_requests": 0,
                "failures": 0,
                "messages": 0
            }

        stats = self.user_behavior[user_id]

        stats["messages"] += 1

        if action in ["delegate", "delegate_multi", "orchestrate"]:
            stats["build_requests"] += 1

        if not success:
            stats["failures"] += 1

    # =========================================================
    # DECIDE IF WE SHOULD UPSELL
    # =========================================================
    def should_pitch(self, user_id):
        now = time.time()

        # Avoid spamming user
        last = self.last_pitch_time.get(user_id, 0)
        if now - last < 60:  # 1 min cooldown
            return False

        stats = self.user_behavior.get(user_id, {})

        # 🔥 Smart triggers
        if stats.get("failures", 0) >= 1:
            return "low_credits"

        if stats.get("build_requests", 0) >= 3:
            return "heavy_usage"

        if stats.get("messages", 0) >= 10:
            return "engaged_user"

        return False

    # =========================================================
    # GENERATE SMART UPSELL MESSAGE
    # =========================================================
    def generate_pitch(self, trigger):
        pitches = {
            "low_credits": [
                "💳 You're running low on credits. Want to keep building without limits?",
                "⚡ You’re out of credits — upgrade to continue creating powerful apps."
            ],
            "heavy_usage": [
                "🚀 You're building a lot! Upgrade to Pro for faster and bigger apps.",
                "🔥 Looks like you're serious — unlock higher limits with Pro."
            ],
            "engaged_user": [
                "✨ You're getting great value from NOX — unlock more power with Pro.",
                "💡 Want priority builds and faster responses? Upgrade your plan."
            ]
        }

        return random.choice(pitches.get(trigger, ["Upgrade to unlock more features 💳"]))

    # =========================================================
    # MAIN ENTRY
    # =========================================================
    def run(self, task):
        user_id = task.get("user_id", "default_user")
        action = task.get("action", "respond")
        success = task.get("success", True)

        # Track behavior
        self.track(user_id, action, success)

        # Decide upsell
        trigger = self.should_pitch(user_id)

        if trigger:
            self.last_pitch_time[user_id] = time.time()

            return {
                "upsell": True,
                "message": self.generate_pitch(trigger),
                "trigger": trigger
            }

        return {
            "upsell": False
        }


# =========================================================
# REGISTER
# =========================================================
def register(runtime):
    agent = MonetizationAgent()
    runtime.register_agent("monetization_agent", agent)

    print("[PLUGIN] Monetization Agent loaded 💰")