import py_compile
import tempfile
import os
from typing import Dict

from ..core.agent import Agent


class Tester(Agent):

    def __init__(self, bus, context):
        super().__init__(name="tester", bus=bus, context=context)

    # ─────────────────────────────────────────────
    def register(self) -> None:
        print("[Tester] Subscribed → CODE_GENERATED, CODE_FIXED")
        self.bus.subscribe("CODE_GENERATED", self.handle)
        self.bus.subscribe("CODE_FIXED", self.handle)

    # ─────────────────────────────────────────────
    def classify_error(self, stderr: str):

        if not stderr:
            return "unknown"

        s = stderr.lower()

        if "syntaxerror" in s:
            return "syntax_error"
        if "no module named" in s:
            return "missing_import"
        if "filenotfounderror" in s:
            return "file_missing"
        if "timeout" in s:
            return "timeout"

        return "runtime_error"

    # ─────────────────────────────────────────────
    async def handle(self, message: dict):

        if message.get("type") not in ["CODE_GENERATED", "CODE_FIXED"]:
            return

        payload = message.get("payload", {})

        files: Dict[str, str] = payload.get("files", {})
        task: str = payload.get("task", "")
        attempts: int = payload.get("fix_attempts", 0)
        user_id: str = payload.get("user_id", "default_user")

        print(f"[Tester] Running test (attempt {attempts})")

        stderr = ""
        passed = False

        try:
            with tempfile.TemporaryDirectory() as tmpdir:

                # Write files
                for path, code in files.items():
                    full = os.path.join(tmpdir, path)
                    os.makedirs(os.path.dirname(full), exist_ok=True)

                    with open(full, "w", encoding="utf-8") as f:
                        f.write(code)

                # Compile Python files
                for path in files:
                    if path.endswith(".py"):
                        py_compile.compile(
                            os.path.join(tmpdir, path),
                            doraise=True
                        )

                passed = True

        except Exception as e:
            stderr = str(e)

        error_type = self.classify_error(stderr)

        print(f"[Tester] {'PASSED' if passed else 'FAILED'} → {error_type}")

        # 🔥 PUBLISH DICT EVENT
        await self.bus.publish({
            "type": "TEST_RESULTS",
            "sender": self.name,
            "payload": {
                "files": files,
                "task": task,
                "passed": passed,
                "stderr": stderr,
                "error_type": error_type,
                "fix_attempts": attempts,
                "user_id": user_id
            }
        })