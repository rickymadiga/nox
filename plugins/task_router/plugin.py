from .agent import TaskRouterAgent


def register(runtime):

    agent = TaskRouterAgent(runtime)

    runtime.register_agent("task_router", agent)