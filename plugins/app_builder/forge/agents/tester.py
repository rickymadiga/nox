import py_compile
import tempfile
import os
from typing import Any, Dict

from ..core.agent import Agent
from ..core.message import Message


class Tester(Agent):

    def register(self) -> None:
        self.bus.subscribe("CODE_GENERATED", self.handle)
        self.bus.subscribe("CODE_FIXED", self.handle)

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

    async def handle(self, message: Message):

        payload = message.payload or {}

        files = payload.get("files", {})
        task = payload.get("task", "")
        attempts = payload.get("fix_attempts", 0)

        print(f"[Tester] Running test (attempt {attempts})")

        stderr = ""
        passed = False

        try:
            with tempfile.TemporaryDirectory() as tmpdir:

                for path, code in files.items():
                    full = os.path.join(tmpdir, path)
                    os.makedirs(os.path.dirname(full), exist_ok=True)

                    with open(full, "w") as f:
                        f.write(code)

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
                },
            )
        )