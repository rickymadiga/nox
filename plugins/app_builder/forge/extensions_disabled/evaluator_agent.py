# forge/extensions/evaluator_agent.py

"""
EvaluatorAgent – Scores and critiques generated code or solutions.
This is an optional extension – can be enabled via config or CLI flag.
"""

from typing import Dict, Any, List, Optional


class EvaluatorAgent:

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.min_score_threshold = self.config.get("min_score_threshold", 70)

    def evaluate(
        self,
        code: str,
        task_description: str,
        execution_result: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Evaluate code against the task – improved with execution weight.
        """

        metrics = {
            "completeness": 0.0,
            "correctness": 0.0,
            "style": 0.0,
            "error_handling": 0.0,
            "execution_success": 0.0
        }

        comments: List[str] = []

        # Completeness
        if len(code.strip()) < 20:
            comments.append("Code is too short – likely incomplete")
            metrics["completeness"] = 20.0
        elif "def " in code or "class " in code or "import " in code:
            metrics["completeness"] = 85.0
        else:
            metrics["completeness"] = 60.0

        # Correctness (placeholder)
        metrics["correctness"] = 80.0

        # Style
        if "TODO" in code or "# TODO" in code:
            comments.append("Contains TODO comments – needs cleanup")
            metrics["style"] = 50.0
        else:
            metrics["style"] = 85.0

        # Error handling
        if "try:" in code and "except" in code:
            metrics["error_handling"] = 90.0
            comments.append("Has try/except – good error handling")
        else:
            metrics["error_handling"] = 40.0
            comments.append("No visible error handling")

        # Execution success
        if execution_result:
            if execution_result.get("returncode") == 0 and not execution_result.get("exception"):
                metrics["execution_success"] = 100.0
                comments.append("Code executed perfectly")
            elif execution_result.get("returncode") != 0:
                metrics["execution_success"] = 20.0
                comments.append(
                    f"Execution failed (code {execution_result.get('returncode')})"
                )
            else:
                metrics["execution_success"] = 50.0
        else:
            metrics["execution_success"] = 0.0
            comments.append("No execution result provided")

        # Weighted score
        total = (
            metrics["completeness"] * 0.15 +
            metrics["correctness"] * 0.15 +
            metrics["style"] * 0.15 +
            metrics["error_handling"] * 0.15 +
            metrics["execution_success"] * 0.40
        )

        return {
            "total_score": round(total, 1),
            "metrics": metrics,
            "comments": comments,
            "passes_threshold": total >= self.min_score_threshold
        }