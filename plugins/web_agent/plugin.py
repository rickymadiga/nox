from .agent import WebAgent


def register(runtime):
    agent = WebAgent(
        name="web_agent",
        bus=runtime.bus,
        context={}
    )

    runtime.register_agent("web_agent", agent)

    print("[Plugin] WebAgent registered ✓")