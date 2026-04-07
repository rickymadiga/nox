from ..core.agent import Agent
from ..core.message import Message

class Reviewer(Agent):

    MAX_FIX_ATTEMPTS = 2

    def register(self) -> None:
        self.bus.subscribe("TEST_RESULTS", self.handle)

    async def handle(self, message: Message):

        if message.message_type != "TEST_RESULTS":
            return

        payload = message.payload or {}
        passed = payload.get("passed", False)
        issues = payload.get("issues", [])
        attempts = payload.get("fix_attempts", 0)

        print(f"[Reviewer] Passed={passed} | Attempts={attempts}")

        # ✅ PASS → assembler
        if passed:
            print("[Reviewer] ✅ Approved")

            await self.bus.publish(
                Message(
                    sender=self.name,
                    recipient="assembler",
                    message_type="CODE_APPROVED",
                    payload=payload,
                )
            )
            return

        # 🔁 TRY FIXER FIRST
        if attempts < self.MAX_FIX_ATTEMPTS:
            print("[Reviewer] 🔁 Sending to fixer")

            await self.bus.publish(
                Message(
                    sender=self.name,
                    recipient="fixer",
                    message_type="REVIEW_FAILED",
                    payload=payload,
                )
            )
            return

        # 🧠 ESCALATE TO DEBUGGER
        print("[Reviewer] 🧠 Escalating to debugger")

        await self.bus.publish(
            Message(
                sender=self.name,
                recipient="debugger",
                message_type="REVIEW_FAILED",
                payload=payload,
            )
        )