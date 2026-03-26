from .agent import CodeAgent


def register(runtime):
    agent = CodeAgent(runtime)

    runtime.register_agent("code_agent", agent)

    print("[PLUGIN] code_agent loaded (UX layer) 🔥")