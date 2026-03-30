from typing import Dict

from ..core.agent import Agent


class Debugger(Agent):

    MAX_ATTEMPTS = 4

    def __init__(self, bus, context):
        super().__init__(name="debugger", bus=bus, context=context)

    # ─────────────────────────────────────────────
    def register(self) -> None:
        print("[Debugger] Intelligent Debugger ready 🔥")
        self.bus.subscribe("REVIEW_COMPLETED", self.handle)

    # ─────────────────────────────────────────────
    async def handle(self, message: dict) -> None:
        if message.get("type") != "REVIEW_COMPLETED":
            return

        payload = message.get("payload", {})

        files: Dict[str, str] = payload.get("files", {})
        task: str = payload.get("task", "")
        error_type: str = payload.get("error_type", "unknown")
        attempts: int = payload.get("fix_attempts", 0)
        passed: bool = payload.get("passed", False)
        user_id: str = payload.get("user_id", "default_user")

        print(f"[Debugger] Attempt {attempts} | Type: {error_type}")

        # ✅ SUCCESS → Send to Assembler
        if passed:
            await self.bus.publish({
                "type": "CODE_APPROVED",
                "sender": self.name,
                "payload": payload
            })
            return

        # 🛑 MAX ATTEMPTS → force approve
        if attempts >= self.MAX_ATTEMPTS:
            print("[Debugger] Max attempts reached → fallback approve")

            await self.bus.publish({
                "type": "CODE_APPROVED",
                "sender": self.name,
                "payload": payload
            })
            return

        # 🧠 ROUTING LOGIC
        if error_type in ["syntax_error", "missing_import", "runtime_error"]:
            next_agent = "fixer"
        elif error_type in ["timeout", "logic_error"]:
            next_agent = "coder"
        else:
            next_agent = "fixer"

        print(f"[Debugger] Routing → {next_agent}")

        # 🔥 FORWARD EVENT
        await self.bus.publish({
            "type": "REVIEW_COMPLETED",
            "sender": self.name,
            "payload": {
                **payload,
                "fix_attempts": attempts + 1,
                "user_id": user_id
            }
        })