import asyncio

class ToolExecutor:
    def __init__(self, tools):
        self.tools = tools

    def execute(self, tool_name, **kwargs):
        tool = self.tools.get(tool_name)

        if not tool:
            raise ValueError(f"Tool {tool_name} not found")

        return asyncio.create_task(tool.handler(**kwargs))