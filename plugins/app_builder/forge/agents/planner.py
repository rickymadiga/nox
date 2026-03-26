# forge/agents/planner.py

from typing import List

from ..agents.base_agent import BaseAgent    # assuming this is your correct base
from ..core.message import Message


class PlannerAgent(BaseAgent):
    """
    Planner agent:
    - Receives TASK_REQUEST
    - Chooses a basic template type (cli / fastapi / streamlit)
    - Creates a very simple fixed plan
    - Publishes PLAN_CREATED to coder
    """

    def register(self) -> None:
        print("[Planner] Subscribing to TASK_REQUEST")
        self.bus.subscribe("TASK_REQUEST", self.handle)

    def _detect_template(self, task: str) -> str:
        """
        Very simple keyword-based template selector.
        Returns one of: 'cli', 'fastapi', 'streamlit'
        """
        task_lower = task.lower().strip()

        if not task_lower:
            return "cli"

        if any(word in task_lower for word in ["api", "backend", "rest", "server", "endpoint"]):
            return "fastapi"

        if any(word in task_lower for word in ["dashboard", "data app", "streamlit", "ui", "web app", "visualization"]):
            return "streamlit"

        # default
        return "cli"

    async def handle(self, message: Message) -> None:
        if message.message_type != "TASK_REQUEST":
            return

        payload = message.payload or {}
        task: str = payload.get("task", "").strip()

        if not task:
            print("[Planner] Received empty task → skipping")
            return

        print(f"[Planner] Received task: {task}")

        template = self._detect_template(task)
        print(f"[Planner] Selected template: {template}")

        # Very basic fixed plan (same logic as original)
        plan: List[str] = [
            "Understand the task requirements",
            "Design the overall program structure",
            "Implement core functionality",
            "Ensure proper entry point (if __name__ == '__main__') exists"
        ]

        # Optional: could enrich plan depending on template in the future
        if template != "cli":
            plan.insert(2, f"Set up {template} application skeleton")

        await self.bus.publish(
            Message(
                sender=self.name,
                recipient="coder",
                message_type="PLAN_CREATED",
                payload={
                    "task": task,
                    "template": template,           # added — useful for coder later
                    "plan": plan
                }
            )
        )

        print("[Planner] PLAN_CREATED published")