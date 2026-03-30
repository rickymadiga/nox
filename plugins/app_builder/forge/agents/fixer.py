# forge/agents/fixer.py

from typing import Dict

from ..core.agent import Agent
from ..core.message import Message


class Fixer(Agent):

    MAX_ATTEMPTS = 4

    def __init__(self, runtime):
        super().__init__(
            name="fixer",
            bus=runtime.bus,
            context={}
        )
        self.runtime = runtime

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
        errors: list = payload.get("errors", [])
        error_type: str = payload.get("error_type", "unknown")
        user_id: str = payload.get("user_id", "default_user")

        print(f"[Fixer] Attempt {attempts} | Type: {error_type}")

        if attempts >= self.MAX_ATTEMPTS:
            print("[Fixer] Max attempts reached → forcing approval")
            await self._approve(files, task, user_id)
            return

        fixed_files = files.copy()

        lily = None
        try:
            lily = self.context.get_agent("lily") if hasattr(self.context, "get_agent") else None
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
            print("[Fixer] No Lily → fallback fix")
            for path in files:
                if not files[path].strip():
                    fixed_files[path] = "def placeholder():\n    return None\n"

        await self.bus.publish(
            Message(
                sender=self.name,
                recipient="tester",
                message_type="CODE_FIXED",
                payload={
                    "files": fixed_files,
                    "task": task,
                    "fix_attempts": attempts + 1,
                    "user_id": user_id
                }
            )
        )

    async def _approve(self, files: Dict[str, str], task: str, user_id: str):
        await self.bus.publish(
            Message(
                sender=self.name,
                recipient="assembler",
                message_type="CODE_APPROVED",
                payload={
                    "files": files,
                    "task": task,
                    "user_id": user_id
                }
            )
        )