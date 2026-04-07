class Tool:
    def __init__(self, name, description, handler):
        self.name = name
        self.description = description
        self.handler = handler


class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, tool: Tool):
        self.tools[tool.name] = tool

    def get(self, name: str):
        return self.tools.get(name)

    def list_descriptions(self):
        return "\n".join(
            f"{name}: {tool.description}"
            for name, tool in self.tools.items()
        )