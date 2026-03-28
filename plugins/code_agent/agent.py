import asyncio
from collections import defaultdict


class CodeAgent:
    def __init__(self, runtime):
        self.runtime = runtime

        # each user gets its own stream queue
        self.queues = defaultdict(asyncio.Queue)

        # subscribe to forge events
        self.runtime.bus.subscribe("forge_update", self.on_update)
        self.runtime.bus.subscribe("forge_complete", self.on_complete)

    # ─────────────────────────────
    async def run(self, task):
        if not isinstance(task, dict):
            return {"error": "Invalid task"}

        prompt = task.get("prompt", "")
        user_id = task.get("user_id", "default_user")

        self._push(user_id, f"🚀 Starting: {prompt}")

        return {
            "agent": "code_agent",
            "message": f"Processing: {prompt}"
        }

    # ─────────────────────────────
    def _push(self, user_id, message):
        try:
            if not user_id:
                user_id = "default_user"

            self.queues[user_id].put_nowait(message)
        except Exception:
            pass

    # ─────────────────────────────
    def on_update(self, message):
        user_id = message.get("user_id", "default_user")

        log = f"⚙️ {message.get('message')}"
        print(log)

        self._push(user_id, log)

    # ─────────────────────────────
    def on_complete(self, message):
        user_id = message.get("user_id", "default_user")

        download = message.get("download_url") or "No download link"
        log = f"✅ {message.get('message')}\n📦 {download}"

        print(log)
        self._push(user_id, log)