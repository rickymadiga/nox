from .agent import AppBuilderTool


def register(runtime):
    tool = AppBuilderTool(runtime)

    # ✅ ONLY REGISTER AS TOOL
    runtime.register_agent("app_builder",tool)

    runtime.register_tool("app_builder", tool)

    print("[AppBuilder] Registered as TOOL 🚀")