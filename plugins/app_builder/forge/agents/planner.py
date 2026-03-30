# forge/agents/planner.py

from typing import List

from ..agents.base_agent import BaseAgent


class PlannerAgent(BaseAgent):
    """
    Planner agent (DICT EVENT VERSION)

    - Receives TASK_REQUEST
    - Selects template
    - Builds simple plan
    - Publishes PLAN_CREATED
    """

    def __init__(self, bus, context):
        super().__init__(name="planner", bus=bus, context=context)

    # ─────────────────────────────────────────────
    def register(self) -> None:
        print("[Planner] Subscribing → TASK_REQUEST")
        self.bus.subscribe("TASK_REQUEST", self.handle)

    # ─────────────────────────────────────────────
    def _detect_template(self, task: str) -> str:
        task_lower = task.lower().strip()

        if not task_lower:
            return "cli"

        if any(word in task_lower for word in ["api", "backend", "rest", "server", "endpoint"]):
            return "fastapi"

        if any(word in task_lower for word in ["dashboard", "data app", "streamlit", "ui", "web app", "visualization"]):
            return "streamlit"

        return "cli"

    # ─────────────────────────────────────────────
    async def handle(self, message: dict) -> None:
        if message.get("type") != "TASK_REQUEST":
            return

        payload = message.get("payload", {})

        task: str = payload.get("task", "").strip()
        user_id: str = payload.get("user_id", "default_user")

        if not task:
            print("[Planner] Empty task → skipping")
            return

        print(f"[Planner] Received task: {task}")

        template = self._detect_template(task)
        print(f"[Planner] Selected template: {template}")

        plan: List[str] = [
            "Understand the task requirements",
            "Design the overall program structure",
            "Implement core functionality",
            "Ensure proper entry point exists"
        ]

        if template != "cli":
            plan.insert(2, f"Set up {template} application skeleton")

        # 🔥 PUBLISH DICT EVENT
        await self.bus.publish({
            "type": "PLAN_CREATED",
            "sender": self.name,
            "payload": {
                "task": task,
                "template": template,
                "plan": plan,
                "user_id": user_id
            }
        })

        print("[Planner] PLAN_CREATED published")