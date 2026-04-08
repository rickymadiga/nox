from typing import Any
from nox.core.agent import Agent  # ✅ correct base
from .forge.arena.arena import run_forge


class AppBuilderTool(Agent):

    def __init__(self, runtime):
        super().__init__(runtime)  # ✅ FIX: match runtime Agent signature
        self.name = "app_builder"  # ✅ manually set name if needed

    def register(self):
        # Optional: depends on runtime design
        pass

    async def run(self, task: Any, user_id: str = "default_user"):

        # ✅ HANDLE INPUT FLEXIBLY
        if isinstance(task, dict):
            user_id = task.get("user_id", "default_user")
            prompt = task.get("prompt") or task.get("input") or ""
        else:
            prompt = str(task)

        print(f"[AppBuilder] 🚀 Starting build for: {prompt} (user: {user_id})")

        result = await run_forge(
            task=prompt,
            runtime=self.runtime,
            user_id=user_id
        )

        return result