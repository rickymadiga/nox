from .agent import ForgeWatcher


def register(runtime):
    agent = ForgeWatcher(runtime)
    runtime.register_agent("ForgeWatcher", agent)

    print("[PLUGIN] ForgeWatcher loaded")