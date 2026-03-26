from .agent import AppBuilderAgent


def register(runtime):

    agent = AppBuilderAgent(runtime)

    runtime.register_agent("app_builder", agent)

    runtime.register_capability(
        agent_name="app_builder",
        intent="app_building",
        keywords=["build app", "create app", "generate app"]
    )