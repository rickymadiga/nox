from .agent import PlannerAgent


def register(runtime):

    agent = PlannerAgent(runtime)

    runtime.register_agent("planner", agent)

    runtime.register_capability(
        agent_name="planner",
        intent="planning",
        keywords=[
            "strategy",
            "steps",
            "disabled",
            "break down task",
        ]
    )