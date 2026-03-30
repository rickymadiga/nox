# forge/agents/tester.py

import py_compile
import tempfile
import os
from typing import Dict

from ..core.agent import Agent
from ..core.message import Message


class Tester(Agent):

    def __init__(self, runtime):
        super().__init__(
            name="tester",
            bus=runtime.bus,
            context={}
        )
        self.runtime = runtime

    def register(self) -> None:
        print("[Tester] Subscribed → CODE_GENERATED, CODE_FIXED")
        self.bus.subscribe("CODE_GENERATED", self.handle)
        self.bus.subscribe("CODE_FIXED", self.handle)

    def classify_error(self, stderr: str) -> str:
        if not stderr:
            return "none"

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

    async def handle(self, message: Message):
        if message.message_type not in ["CODE_GENERATED", "CODE_FIXED"]:
            return

        payload = message.payload or {}

        files: Dict[str, str] = payload.get("files", {})
        task: str = payload.get("task", "")
        attempts: int = payload.get("fix_attempts", 0)
        user_id: str = payload.get("user_id", "default_user")

        print(f"[Tester] Running test (attempt {attempts})")

        stderr = ""
        passed = False
        error_type = "none"                    # ← Default value to prevent UnboundLocalError

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Write all files
                for path, code in files.items():
                    full = os.path.join(tmpdir, path)
                    os.makedirs(os.path.dirname(full), exist_ok=True)
                    with open(full, "w", encoding="utf-8") as f:
                        f.write(code)

                # Compile check for Python files
                for path in files:
                    if path.endswith(".py"):
                        py_compile.compile(
                            os.path.join(tmpdir, path),
                            doraise=True
                        )

                passed = True
                print("[Tester] All files compiled successfully")

        except Exception as e:
            stderr = str(e)
            print(f"[Tester] Test failed: {e}")

        error_type = self.classify_error(stderr)

        print(f"[Tester] {'PASSED' if passed else 'FAILED'} → {error_type}")

        # Publish result
        await self.bus.publish(
            Message(
                sender=self.name,
                recipient="reviewer",
                message_type="TEST_RESULTS",
                payload={
                    "files": files,
                    "task": task,
                    "passed": passed,
                    "stderr": stderr,
                    "error_type": error_type,
                    "fix_attempts": attempts,
                    "user_id": user_id
                }
            )
        )