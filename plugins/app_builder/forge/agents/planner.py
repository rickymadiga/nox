from typing import List

from ..agents.base_agent import BaseAgent
from ..core.message import Message


class PlannerAgent(BaseAgent):

    def register(self) -> None:
        print("[Planner] Subscribing to TASK_REQUEST")
        self.bus.subscribe("TASK_REQUEST", self.handle)

    # ─────────────────────────────────────────────
    def _detect_template(self, task: str) -> str:
        task_lower = task.lower().strip()

        if any(word in task_lower for word in ["api", "backend", "server", "endpoint"]):
            return "fastapi"

        if any(word in task_lower for word in ["app", "ui", "dashboard", "web", "streamlit"]):
            return "streamlit"

        return "cli"

    # ─────────────────────────────────────────────
    def _build_plan(self, template: str) -> List[str]:

        if template == "streamlit":
            return [
                "Create a Streamlit app using main.py",
                "Use st.title, inputs, and UI components",
                "Do NOT include if __name__ == '__main__'",
                "Ensure code runs with 'streamlit run main.py'"
            ]

        if template == "fastapi":
            return [
                "Create FastAPI app in main.py",
                "Define routes and endpoints",
                "Use uvicorn to run the app",
                "Ensure requirements.txt includes fastapi and uvicorn"
            ]

        # CLI default
        return [
            "Create CLI-based Python script",
            "Include main() function",
            "Use if __name__ == '__main__' entry point"
        ]

    # ─────────────────────────────────────────────
    async def handle(self, message: Message) -> None:

        if message.message_type != "TASK_REQUEST":
            return

        payload = message.payload or {}

        task: str = payload.get("task", "").strip()
        user_id: str = payload.get("user_id", "default_user")

        if not task:
            print("[Planner] Empty task → skipping")
            return

        print(f"[Planner] Task: {task}")

        template = self._detect_template(task)
        plan = self._build_plan(template)

        print(f"[Planner] Template → {template}")

        # ─────────────────────────────────────────
        # 🔥 SEND TO CODER (FIXED)
        # ─────────────────────────────────────────
        await self.bus.publish(
            Message(
                sender=self.name,
                recipient="coder",
                message_type="PLAN_CREATED",
                payload={
                    "task": task,
                    "user_id": user_id,        # ✅ CRITICAL FIX
                    "template": template,
                    "plan": plan
                }
            )
        )

        print("[Planner] PLAN_CREATED published")