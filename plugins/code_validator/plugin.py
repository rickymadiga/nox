from .agent import CodeValidatorAgent


def register(runtime):

    agent = CodeValidatorAgent(runtime)

    runtime.register_agent("code_validator", agent)

    runtime.register_capability(
        agent_name="code_validator",
        intent="code_validation",
        keywords=[
            "validate code",
            "check code",
            "code review",
            "debug code"
        ]
    )