import asyncio
from collections import defaultdict


class CodeAgent:

    def __init__(self, runtime):
        self.runtime = runtime

        # 🔥 each user gets its own stream queue
        self.queues = defaultdict(asyncio.Queue)

        # subscribe to forge events
        self.runtime.bus.subscribe("forge_update", self.on_update)
        self.runtime.bus.subscribe("forge_complete", self.on_complete)


    # ─────────────────────────────
    def _push(self, user_id, message):
        try:
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

        log = f"✅ {message.get('message')}\n📦 {message.get('download_url')}"
        print(log)

        self._push(user_id, log)


    # ─────────────────────────────
    async def stream(self, user_id):
        queue = self.queues[user_id]

        while True:
            msg = await queue.get()
            yield msg