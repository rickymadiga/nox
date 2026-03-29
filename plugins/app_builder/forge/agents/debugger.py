from typing import Any, Dict

from ..core.agent import Agent
from ..core.message import Message


class Debugger(Agent):

    MAX_ATTEMPTS = 4

    def register(self) -> None:
        print("[Debugger] Intelligent Debugger ready 🔥")
        self.bus.subscribe("REVIEW_COMPLETED", self.handle)

    async def handle(self, message: Message) -> None:
        payload = message.payload or {}

        files: Dict[str, str] = payload.get("files", {})
        task: str = payload.get("task", "")
        error_type: str = payload.get("error_type", "unknown")
        attempts: int = payload.get("fix_attempts", 0)
        passed: bool = payload.get("passed", False)

        print(f"[Debugger] Attempt {attempts} | Type: {error_type}")

        # ✅ SUCCESS - Tests passed
        if passed:
            await self.bus.publish(
                Message(
                    sender=self.name,
                    recipient="assembler",
                    message_type="CODE_APPROVED",
                    payload=payload,
                )
            )
            return

        # 🛑 STOP CONDITION - Max attempts reached
        if attempts >= self.MAX_ATTEMPTS:
            print("[Debugger] Max attempts reached → safe fallback")
            await self.bus.publish(
                Message(
                    sender=self.name,
                    recipient="assembler",
                    message_type="CODE_APPROVED",
                    payload=payload,
                )
            )
            return

        # 🧠 DECISION LOGIC - Route based on error type
        if error_type in ["syntax_error", "missing_import", "runtime_error"]:
            next_agent = "fixer"
        elif error_type in ["timeout", "logic_error"]:
            next_agent = "coder"
        else:
            next_agent = "fixer"

        print(f"[Debugger] Routing → {next_agent}")

        # Forward to next agent (Fixer or Coder)
        await self.bus.publish(
            Message(
                sender=self.name,
                recipient=next_agent,
                message_type="REVIEW_COMPLETED",
                payload={
                    **payload,
                    "fix_attempts": attempts + 1,
                },
            )
        )