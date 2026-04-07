# tester.py (or forge/agents/tester.py)

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

    # ─────────────────────────────────────────────
    # 🧠 SMART ANALYSIS (TEMPLATE-AWARE)
    # ─────────────────────────────────────────────
    def analyze_code(self, files: Dict[str, str], template: str = None):
        issues = []

        for path, code in files.items():
            if not path.endswith(".py"):
                continue

            # ❌ Unused pandas
            if "import pandas" in code and "pd." not in code:
                issues.append("Unused import: pandas")

            # ───────── STREAMLIT RULES ─────────
            if template == "streamlit":
                if "st." not in code:
                    issues.append("Streamlit not used properly")

                # non-critical (UX improvement)
                if "st.button" not in code:
                    issues.append("Missing st.button trigger (non-critical)")

                # ❌ should NOT exist in Streamlit apps
                if "__name__" in code and "__main__" in code:
                    issues.append("Remove __main__ block for Streamlit")

            # ───────── FASTAPI RULES ─────────
            elif template == "fastapi":
                if "FastAPI" not in code and "fastapi" not in code.lower():
                    issues.append("FastAPI not used properly")
                if "app =" not in code.lower() and "APIRouter" not in code:
                    issues.append("Missing FastAPI app or router")

            # ───────── CLI RULES ─────────
            elif template == "cli" or template is None:   # None = default CLI from Coder
                if "__name__" not in code or "__main__" not in code:
                    issues.append("Missing __main__ entry point")

            # ❌ Weak error handling
            if "return 'Error'" in code or "return \"Error\"" in code:
                issues.append("Weak error handling")

        # ❌ Missing requirements.txt
        if "requirements.txt" not in files:
            issues.append("Missing requirements.txt")

        return issues

    # ─────────────────────────────────────────────
    async def handle(self, message: Message):

        payload = message.payload or {}
        files = payload.get("files", {})
        task = payload.get("task", "")
        attempts = payload.get("fix_attempts", 0)
        template = payload.get("template")
        user_id = payload.get("user_id", "default_user")

        print(f"[Tester] Running test (attempt {attempts})")

        stderr = ""
        syntax_passed = False

        # ───────── SYNTAX CHECK ─────────
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                for path, code in files.items():
                    full = os.path.join(tmpdir, path)
                    os.makedirs(os.path.dirname(full), exist_ok=True)

                    with open(full, "w", encoding="utf-8") as f:
                        f.write(code)

                for path in files:
                    if path.endswith(".py"):
                        py_compile.compile(
                            os.path.join(tmpdir, path),
                            doraise=True
                        )

                syntax_passed = True

        except Exception as e:
            stderr = str(e)

        # ───────── ANALYSIS ─────────
        issues = self.analyze_code(files, template)

        # ───────── SMART PASS LOGIC ─────────
        # Keep your original intent but make it more reliable
        critical_issues = [
            i for i in issues
            if "Missing requirements" in i
            or "syntax" in stderr.lower()
            or "Streamlit not used properly" in i
            or "FastAPI not used properly" in i
            or "Missing __main__ entry point" in i
        ]

        passed = syntax_passed and len(critical_issues) == 0

        print(f"[Tester] {'PASSED' if passed else 'FAILED'}")
        print(f"[Tester] Issues: {issues}")

        # ───────── PUBLISH RESULTS ─────────
        await self.bus.publish(
            Message(
                sender=self.name,
                recipient="reviewer",
                message_type="TEST_RESULTS",
                payload={
                    "files": files,
                    "task": task,
                    "passed": passed,
                    "issues": issues,
                    "stderr": stderr,
                    "fix_attempts": attempts,
                    "user_id": user_id,
                    "template": template,
                },
            )
        )