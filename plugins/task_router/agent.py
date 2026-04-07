class TaskRouterAgent:

    def __init__(self, runtime):
        self.runtime = runtime


    async def run(self, task):

        prompt = ""

        if isinstance(task, dict):
            prompt = task.get("prompt", "")
        else:
            prompt = getattr(task, "prompt", "")

        capability_index = self.runtime.capability_index

        matched_agents = capability_index.match(prompt)

        if not matched_agents:
            return {
                "agent": "task_router",
                "error": "No matching agent found"
            }

        return {
            "agent": "task_router",
            "agents": matched_agents
        }