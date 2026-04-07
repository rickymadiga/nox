class CodeValidatorAgent:

    def __init__(self, runtime):
        self.runtime = runtime

    async def run(self, task):

        prompt = ""

        if isinstance(task, dict):
            prompt = task.get("prompt", "")
        else:
            prompt = getattr(task, "prompt", "")

        if "error" in prompt.lower():
            status = "Code might contain errors"
        else:
            status = "Code appears valid"

        return {
            "agent": "code_validator",
            "validation": status
        }