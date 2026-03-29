import asyncio
from collections import defaultdict


class CodeAgent:
    def __init__(self, runtime):
        self.runtime = runtime
        self.bus = runtime.bus

        # each user gets its own stream queue
        self.queues = defaultdict(asyncio.Queue)

    # ─────────────────────────────
    def register(self):
        self.bus.subscribe("forge_update", self.on_update)
        self.bus.subscribe("forge_complete", self.on_complete)

        print("[CodeAgent] Subscribed to forge events")

    # ─────────────────────────────
    async def run(self, task):
        if not isinstance(task, dict):
            return {"error": "Invalid task"}

        prompt = task.get("prompt", "")
        user_id = task.get("user_id", "default_user")

        self._push(user_id, f"🚀 Starting: {prompt}")

        # 🔥 Trigger forge pipeline here if needed
        # await self.runtime.run_forge(prompt)

        return {
            "agent": "code_agent",
            "message": f"Processing: {prompt}"
        }

    # ─────────────────────────────
    def _push(self, user_id, message):
        if not user_id:
            user_id = "default_user"

        if user_id not in self.queues:
            self.queues[user_id] = asyncio.Queue()

        try:
            self.queues[user_id].put_nowait(message)
        except Exception as e:
            print(f"[CodeAgent] Queue error: {e}")

    # ─────────────────────────────
    def _extract(self, message):
        """
        Normalize Message or dict → dict
        """
        if hasattr(message, "payload"):
            return message.payload
        return message or {}

    # ─────────────────────────────
    def on_update(self, message):
        data = self._extract(message)

        user_id = data.get("user_id", "default_user")
        log = f"⚙️ {data.get('message', '')}"

        print(log)
        self._push(user_id, log)

    # ─────────────────────────────
    def on_complete(self, message):
        data = self._extract(message)

        user_id = data.get("user_id", "default_user")
        download = data.get("download_url") or "No download link"

        log = f"✅ {data.get('message', '')}\n📦 {download}"

        print(log)
        self._push(user_id, log)