from typing import Dict

from ..core.agent import Agent


class Reviewer(Agent):

    def __init__(self, bus, context):
        super().__init__(name="reviewer", bus=bus, context=context)

    # ─────────────────────────────────────────────
    def register(self) -> None:
        print("[Reviewer] Subscribed → TEST_RESULTS")
        self.bus.subscribe("TEST_RESULTS", self.handle)

    # ─────────────────────────────────────────────
    async def handle(self, message: dict) -> None:
        if message.get("type") != "TEST_RESULTS":
            return

        payload = message.get("payload", {})

        print("[Reviewer] Passive analysis → forwarding to Debugger")

        # 🔥 Forward to Debugger (broadcast style)
        await self.bus.publish({
            "type": "REVIEW_COMPLETED",
            "sender": self.name,
            "payload": payload
        })