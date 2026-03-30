# forge/agents/reviewer.py

from typing import Dict

from ..core.agent import Agent
from ..core.message import Message


class Reviewer(Agent):

    def __init__(self, runtime):
        super().__init__(
            name="reviewer",
            bus=runtime.bus,
            context={}
        )
        self.runtime = runtime

    def register(self) -> None:
        print("[Reviewer] Subscribed → TEST_RESULTS")
        self.bus.subscribe("TEST_RESULTS", self.handle)

    async def handle(self, message: Message) -> None:
        if message.message_type != "TEST_RESULTS":
            return

        payload = message.payload or {}

        print("[Reviewer] Passive analysis → forwarding to Debugger")

        await self.bus.publish(
            Message(
                sender=self.name,
                recipient="debugger",
                message_type="REVIEW_COMPLETED",
                payload=payload
            )
        )