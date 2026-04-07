from ..core.agent import Agent
from ..core.message import Message

class Debugger(Agent):

    MAX_ATTEMPTS = 3

    def register(self) -> None:
        print("[Debugger] Ready 🔥")
        self.bus.subscribe("REVIEW_FAILED", self.handle)

    async def handle(self, message: Message) -> None:

        if message.message_type != "REVIEW_FAILED":
            return

        payload = message.payload or {}

        attempts = payload.get("fix_attempts", 0)
        issues = payload.get("issues", [])

        print(f"[Debugger] Attempt {attempts} | Issues: {issues}")

        # 🛑 STOP LOOP (force finish)
        if attempts >= self.MAX_ATTEMPTS:
            print("[Debugger] Max attempts → forcing approval")

            await self.bus.publish(
                Message(
                    sender=self.name,
                    recipient="assembler",
                    message_type="CODE_APPROVED",
                    payload=payload
                )
            )
            return

        # 🧠 smarter routing
        if any("syntax" in i.lower() for i in issues):
            next_agent = "fixer"
        elif any("logic" in i.lower() for i in issues):
            next_agent = "coder"
        else:
            next_agent = "fixer"

        print(f"[Debugger] Routing → {next_agent}")

        await self.bus.publish(
            Message(
                sender=self.name,
                recipient=next_agent,
                message_type="CODE_FIX_REQUEST",
                payload={
                    **payload,
                    "fix_attempts": attempts + 1
                }
            )
        )