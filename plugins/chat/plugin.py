from .agent import ChatAgent


def register(runtime):

    agent = ChatAgent(runtime)

    runtime.register_agent(
        "chat",
        agent
    )

    runtime.register_capability(
        agent_name="chat",
        intent="general_knowledge",
        keywords=[
            "explain",
            "tell me about",
            "what is",
            "why",
            "who",
            "history",
            "science",
            "technology"
        ]
    )

    runtime.capabilities.set_priority(
        "chat",
        50
    )