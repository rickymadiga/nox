from .agent import AnalyticsAgent


def register(runtime):

    agent = AnalyticsAgent(runtime)

    runtime.register_agent("analytics", agent)

    runtime.register_capability(
        agent_name="analytics",
        intent="math",
        keywords=[
            "calculate",
            "sum",
            "average",
            "multiply",
            "add",
            "subtract",
            "divide",
            "statistics",
            "math"
        ]
    )

    runtime.capabilities.set_priority("analytics", 10)