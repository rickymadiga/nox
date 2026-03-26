from .agent import Lily
from nox.core.llm import SimpleLLM


def register(runtime):

    llm = SimpleLLM

    agent = Lily(runtime, llm=llm)

    runtime.register_agent("lily", agent)

    runtime.register_capability(
        agent_name="lily",
        intent="orchestrator",
        keywords=[
            "chat", "talk", "assistant",
            "help", "build", "create",
            "analyze", "fix", "code"
        ],
        priority=100  # 🔥 VERY IMPORTANT
    )