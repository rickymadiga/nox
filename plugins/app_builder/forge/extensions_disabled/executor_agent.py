# forge/extensions/executor_agent.py

"""
ExecutorAgent – Safely runs generated code and returns output / errors.
This is an optional extension – can be enabled via config or CLI flag.
"""

from typing import Dict, Any, Optional, Tuple, List
import subprocess


class ExecutorAgent:
    """
    Executes Python code in a controlled way.

    Phase 1:
        Basic subprocess execution (no sandbox yet)

    Future phases:
        - sandboxed execution
        - container execution
        - restricted environment
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.timeout_seconds = self.config.get("execution_timeout", 30)

    def evaluate(
        self,
        code: str,
        task_description: str,
        execution_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Placeholder evaluation method.

        Later this can:
        - analyze stdout/stderr
        - score execution success
        - feed results back to planner
        """

        return {
            "task": task_description,
            "code_length": len(code),
            "execution_result": execution_result,
            "status": "not_evaluated",
        }

    def execute_code_file(
        self,
        file_path: str,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
    ) -> Tuple[str, str, int, Optional[str]]:
        """
        Run a Python file and return:

        Returns:
            stdout (str)
            stderr (str)
            returncode (int)
            exception_message_if_failed (Optional[str])
        """

        try:
            result = subprocess.run(
                ["python", file_path] + (args or []),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                cwd=cwd,
            )

            return result.stdout, result.stderr, result.returncode, None

        except subprocess.TimeoutExpired:
            return "", "Execution timed out", 124, "TimeoutExpired"

        except Exception as e:
            return "", "", 1, str(e)

    # Future:
    # - container sandbox
    # - restricted python interpreter
    # - memory / cpu limits