# forge/agents/planner.py

from typing import List, Any

from ..core.agent import Agent
from ..core.message import Message


class PlannerAgent(Agent):
    """
    Planner agent - now strictly using Message objects
    """

    def __init__(self, runtime):
        super().__init__(
            name="planner",
            bus=runtime.bus,
            context={}
        )
        self.runtime = runtime

    def register(self) -> None:
        print("[Planner] Subscribing → TASK_REQUEST")
        self.bus.subscribe("TASK_REQUEST", self.handle)

    def _detect_template(self, task: str) -> str:
        task_lower = task.lower().strip()

        if not task_lower:
            return "cli"

        if any(word in task_lower for word in ["api", "backend", "rest", "server", "endpoint"]):
            return "fastapi"

        if any(word in task_lower for word in ["dashboard", "data app", "streamlit", "ui", "web app", "visualization"]):
            return "streamlit"

        return "cli"

    async def handle(self, message: Message) -> None:
        if message.message_type != "TASK_REQUEST":
            return

        payload = message.payload or {}

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

        await self.bus.publish(
            Message(
                sender=self.name,
                recipient="coder",
                message_type="PLAN_CREATED",
                payload={
                    "task": task,
                    "template": template,
                    "plan": plan,
                    "user_id": user_id
                }
            )
        )

        print("[Planner] PLAN_CREATED published")