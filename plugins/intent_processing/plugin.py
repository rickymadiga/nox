from .agent import IntentProcessingAgent


def register(runtime):

    runtime.register_agent(
        "intent_processing",
        IntentProcessingAgent(runtime)
    )

    runtime.register_capability(
        agent_name="intent_processing",
        intent="intent_analysis",
        keywords=[
            "detect intent",
            "analyze intent",
            "classify intent"
        ]
    )