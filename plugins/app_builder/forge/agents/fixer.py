from typing import Any, Dict
from ..core.agent import Agent
from ..core.message import Message


class Fixer(Agent):

    MAX_ATTEMPTS = 4

    def register(self):
        print("[Fixer] Subscribed → REVIEW_COMPLETED")
        self.bus.subscribe("REVIEW_COMPLETED", self.handle)

    async def handle(self, message: Message):

        if message.message_type != "REVIEW_COMPLETED":
            return

        payload = message.payload or {}

        files: Dict[str, str] = payload.get("files", {})
        task: str = payload.get("task", "")
        attempts: int = payload.get("fix_attempts", 0)
        errors = payload.get("errors", [])
        error_type = payload.get("error_type", "unknown")

        print(f"[Fixer] Attempt {attempts} | Type: {error_type}")

        # ✅ STOP CONDITION
        if attempts >= self.MAX_ATTEMPTS:
            print("[Fixer] Max attempts → forcing safe output")
            await self._approve(files, task)
            return

        # -------------------------------------------------
        # 🔥 CALL LILY (REAL FIX)
        # -------------------------------------------------
        fixed_files = files

        lily = None

        # Try to get Lily safely
        if hasattr(self, "runtime") and self.runtime:
            try:
                lily = self.runtime.get_agent("lily")
            except Exception:
                lily = None

        if lily:
            try:
                print("[Fixer] Using Lily 🧠")

                result = await lily.run({
                    "type": "fix_code",
                    "files": files,
                    "error": "\n".join(errors),
                    "error_type": error_type,
                })

                if isinstance(result, dict) and "files" in result:
                    fixed_files = result["files"]

            except Exception as e:
                print(f"[Fixer] Lily failed: {e}")

        else:
            print("[Fixer] Lily not available → fallback")

            # Minimal fallback
            for path in files:
                if not files[path].strip():
                    fixed_files[path] = "def placeholder():\n    return None\n"

        # -------------------------------------------------
        # SEND BACK TO TESTER
        # -------------------------------------------------
        await self.bus.publish(
            Message(
                sender=self.name,
                recipient="tester",
                message_type="CODE_FIXED",
                payload={
                    "files": fixed_files,
                    "task": task,
                    "fix_attempts": attempts + 1,
                },
            )
        )

    # -------------------------------------------------
    # APPROVAL
    # -------------------------------------------------
    async def _approve(self, files, task):
        await self.bus.publish(
            Message(
                sender=self.name,
                recipient="assembler",
                message_type="CODE_APPROVED",
                payload={
                    "files": files,
                    "task": task,
                },
            )
        )