from .agent import NotificationAgent


def register(runtime):

    agent = NotificationAgent(runtime)

    runtime.register_agent("notification", agent)

    runtime.register_capability(
        agent_name="notification",
        intent="notify",
        keywords=[
            "notify",
            "remind",
            "alert",
            "send notification"
        ]
    )