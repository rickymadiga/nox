from .core.runtime import Runtime
from .brain.lily import Lily

# Load tools
from plugins.app_builder.plugin import register as register_app_builder


class Orchestrator:
    def __init__(self):
        self.runtime = Runtime()

        # Register tools
        register_app_builder(self.runtime, self)

        # Brain
        self.lily = Lily(self.runtime)

    def register(self, tool):
        self.runtime.register_tool(tool)

    async def handle(self, user_input: str, user_id="default"):
        return await self.lily.run(user_input, user_id)