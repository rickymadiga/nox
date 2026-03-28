from nox.plugins.app_builder.forge.arena.arena import run_forge


class AppBuilderAgent:
    def __init__(self, runtime):
        self.runtime = runtime

    async def run(self, task):
        try:
            # Ensure valid task
            if not isinstance(task, dict):
                return {
                    "agent": "app_builder",
                    "error": f"Invalid task type: {type(task)}"
                }

            prompt = task.get("prompt", "")
            print(f"[AppBuilder] received prompt: {prompt}")

            result = await run_forge(prompt)

            # Handle forge error
            if isinstance(result, dict) and result.get("error"):
                return {
                    "agent": "app_builder",
                    "error": result["error"]
                }

            return {
                "agent": "app_builder",
                "message": "Project completed successfully",
                "forge_result": result
            }

        except Exception as e:
            return {
                "agent": "app_builder",
                "error": str(e)
            }