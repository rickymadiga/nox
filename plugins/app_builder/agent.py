from plugins.app_builder.forge.arena.arena import run_forge


class AppBuilderAgent:

    def __init__(self, runtime):
        self.runtime = runtime

    async def run(self, task):

        prompt = task.get("prompt", "")

        print(f"[AppBuilder] received prompt: {prompt}")

        result = await run_forge(prompt)

        return {
            "agent": "app_builder",
            "message": "Forge project generation started.",
            "forge_result": result
        }