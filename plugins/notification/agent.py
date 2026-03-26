class NotificationAgent:

    def __init__(self, runtime):
        self.runtime = runtime

    async def run(self, task):

        prompt = ""

        if isinstance(task, dict):
            prompt = task.get("prompt", "")
        else:
            prompt = getattr(task, "prompt", "")

        return {
            "agent": "notification",
            "status": "notification sent",
            "message": prompt
        }