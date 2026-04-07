from typing import Dict

from ..core.agent import Agent
from ..core.message import Message


class Fixer(Agent):

    MAX_ATTEMPTS = 3

    def register(self) -> None:
        print("[Fixer] Subscribed → REVIEW_FAILED")
        self.bus.subscribe("REVIEW_FAILED", self.handle)

    async def handle(self, message: Message):

        if message.message_type != "REVIEW_FAILED":
            return

        payload = message.payload or {}
        files: Dict[str, str] = payload.get("files", {})
        issues: list = payload.get("issues", [])
        attempts = payload.get("fix_attempts", 0)

        print(f"[Fixer] Attempt {attempts + 1} | Issues: {len(issues)} found")

        # 🛑 HARD STOP
        if attempts >= self.MAX_ATTEMPTS:
            print("[Fixer] Max attempts reached → forcing final result")

            await self.bus.publish(
                Message(
                    sender=self.name,
                    recipient="assembler",
                    message_type="CODE_FINAL",          # Better than approving bad code
                    payload={
                        **payload,
                        "final_status": "failed_after_max_attempts"
                    }
                )
            )
            return

        fixed_files = {}

        for path, content in files.items():
            if not path.endswith(".py"):
                fixed_files[path] = content
                continue

            updated = content

            # ─────────────────────────────
            # Apply fixes based on actual issues from Tester
            # ─────────────────────────────
            issue_text = " ".join(issues).lower()

            if "st.button" in issue_text or "streamlit not used" in issue_text:
                updated = self._inject_button_logic(updated)

            if "remove __main__" in issue_text or "__main__" in issue_text:
                updated = self._remove_main_block(updated)

            # General cleanup
            updated = self._normalize_operations(updated)

            fixed_files[path] = updated

        # 🚀 SEND FIXED CODE BACK TO TESTER
        await self.bus.publish(
            Message(
                sender=self.name,
                recipient="tester",
                message_type="CODE_FIXED",
                payload={
                    **payload,
                    "files": fixed_files,
                    "fix_attempts": attempts + 1,
                },
            )
        )

        print(f"[Fixer] ✅ Sent CODE_FIXED (attempt {attempts + 1}) to tester")

    # ─────────────────────────────
    # 🔧 HELPERS (kept mostly as you wrote)
    # ─────────────────────────────

    def _inject_button_logic(self, code: str) -> str:
        """Safe attempt to add button logic for Streamlit."""
        if "st.button" in code:
            return code

        # Simple append approach - less destructive
        button_block = """

if st.button("Calculate"):
    # TODO: Replace with your actual calculation logic
    st.write("Calculation triggered - implement your logic here")
"""

        return code.strip() + "\n" + button_block

    def _remove_main_block(self, code: str) -> str:
        """Remove common __main__ blocks safely."""
        lines = code.splitlines()
        cleaned = []
        skip = False

        for line in lines:
            if "if __name__" in line:
                skip = True
                continue
            if skip and line.strip() == "":
                continue
            if skip and not line.startswith(" "):  # end of block
                skip = False
            if not skip:
                cleaned.append(line)

        return "\n".join(cleaned).strip()

    def _normalize_operations(self, code: str) -> str:
        """Consistent naming."""
        return (
            code.replace("'Addition'", "'Add'")
                .replace("'Subtraction'", "'Subtract'")
                .replace("'Multiplication'", "'Multiply'")
                .replace("'Division'", "'Divide'")
        )