# forge/agents/debugger.py

from ..core.agent import Agent
from ..core.message import Message


class Debugger(Agent):

    MAX_ATTEMPTS = 4

    def __init__(self, runtime):
        super().__init__(
            name="debugger",
            bus=runtime.bus,
            context={}
        )
        self.runtime = runtime

    def register(self) -> None:
        print("[Debugger] Intelligent Debugger ready 🔥")
        self.bus.subscribe("REVIEW_COMPLETED", self.handle)

    async def handle(self, message: Message) -> None:
        if message.message_type != "REVIEW_COMPLETED":
            return

        payload = message.payload or {}

        files = payload.get("files", {})
        task = payload.get("task", "")
        error_type = payload.get("error_type", "unknown")
        attempts = payload.get("fix_attempts", 0)
        passed = payload.get("passed", False)
        user_id = payload.get("user_id", "default_user")

        print(f"[Debugger] Attempt {attempts} | Type: {error_type} | Passed: {passed}")

        # Success conditions: either test passed or error_type is "none"
        if passed or error_type == "none" or attempts >= self.MAX_ATTEMPTS:
            if attempts >= self.MAX_ATTEMPTS:
                print("[Debugger] Max attempts reached → forcing approval")
            else:
                print("[Debugger] Test passed → approving code")

            await self.bus.publish(
                Message(
                    sender=self.name,
                    recipient="assembler",
                    message_type="CODE_APPROVED",
                    payload=payload
                )
            )
            return

        # Decide next agent based on error type
        if error_type in ["syntax_error", "missing_import", "runtime_error"]:
            next_agent = "fixer"
        elif error_type in ["timeout", "logic_error"]:
            next_agent = "coder"
        else:
            next_agent = "fixer"  # default fallback

        print(f"[Debugger] Routing to {next_agent} for fix (attempt {attempts + 1})")

        # Forward with incremented attempt counter
        await self.bus.publish(
            Message(
                sender=self.name,
                recipient=next_agent,
                message_type="REVIEW_COMPLETED",
                payload={
                    **payload,
                    "fix_attempts": attempts + 1,
                    "user_id": user_id
                }
            )
        )