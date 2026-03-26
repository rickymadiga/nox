from typing import Any, Dict

from ..core.agent import Agent
from ..core.message import Message


class Reviewer(Agent):

    def register(self) -> None:
        self.bus.subscribe("TEST_RESULTS", self.handle)

    async def handle(self, message: Message) -> None:

        if message.message_type != "TEST_RESULTS":
            return

        payload = message.payload or {}

        print("[Reviewer] Passive analysis only")

        await self.bus.publish(
            Message(
                sender=self.name,
                recipient="debugger",   # ✅ ALWAYS debugger
                message_type="REVIEW_COMPLETED",
                payload=payload,
            )
        )