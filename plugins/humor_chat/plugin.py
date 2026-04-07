from .agent import HumorAgent


def register(runtime):

    agent = HumorAgent(runtime)

    runtime.register_agent("humor_chat", agent)

    runtime.register_capability(
        agent_name="humor_chat",
        intent="humor",
        keywords=[
            "joke",
            "funny",
            "make me laugh",
            "tell joke",
            "humor"
        ]
    )