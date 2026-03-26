from .bug_fixer_agent import BugFixerAgent

agent = BugFixerAgent()

# Failing code example
bad_code = """
print(undefined_variable)
"""

execution_result = {
    "stdout": "",
    "stderr": "",
    "returncode": 1,
    "exception": "NameError: name 'undefined_variable' is not defined"
}

fix_result = agent.fix_code(bad_code, execution_result)

print("Fix result:")
print(fix_result)