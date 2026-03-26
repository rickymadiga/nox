from .agent import ContentGeneratorAgent


def register(runtime):

    runtime.register_agent(
        "content_generator",
        ContentGeneratorAgent(runtime)
    )

    runtime.register_capability(
        agent_name="content_generator",
        intent="content_generation",
        keywords=[
            "story",
            "write",
            "article",
            "essay",
            "blog",
            "poem",
            "describe"
        ]
    )