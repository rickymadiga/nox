# forge/extensions/test_chain_with_fixer.py

"""
Reusable chain runner:
Executor → Evaluator → (if needed) BugFixer → Archive + Artifact
"""

from typing import Dict, Any
import os
import tempfile

from extensions.executor_agent import ExecutorAgent
from extensions.evaluator_agent import EvaluatorAgent
from extensions.solution_archive_agent import SolutionArchiveAgent
from extensions.artifact_agent import ArtifactAgent
from extensions.bug_fixer_agent import BugFixerAgent


def run_full_chain(task_description: str, dummy_code: str = None) -> Dict[str, Any]:
    """
    Run the full agent chain for a task.

    Returns
    -------
    dict
        {
            "status": str,
            "messages": List[str],
            "build_path": Optional[str]
        }
    """

    result: Dict[str, Any] = {
        "status": "success",
        "messages": [],
        "build_path": None
    }

    # Default code if none provided
    code = dummy_code or """
def add(a, b):
    return a + b

result = add(5, 7)
print(f"5 + 7 = {result}")
"""

    result["messages"].append(f"Task: {task_description}")
    result["messages"].append("Executing original code...")

    # Create temp file for execution
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
        encoding="utf-8"
    ) as tmp:
        tmp.write(code)
        code_path = tmp.name

    try:

        executor = ExecutorAgent({"execution_timeout": 10})

        stdout, stderr, returncode, exc = executor.execute_code_file(code_path)

        exec_result = {
            "stdout": stdout,
            "stderr": stderr,
            "returncode": returncode,
            "exception": exc
        }

        result["messages"].append(
            f"Execution: returncode={returncode}, stdout={stdout.strip()[:100]}"
        )

        evaluator = EvaluatorAgent({"min_score_threshold": 70})

        eval_result = evaluator.evaluate(
            code=code,
            task_description=task_description,
            execution_result=exec_result
        )

        result["messages"].append(
            f"Evaluation score: {eval_result.get('total_score')}"
        )

        result["messages"].append(
            f"Passes threshold: {eval_result.get('passes_threshold')}"
        )

        current_code = code
        current_eval = eval_result

        # ---- FIX ATTEMPT ----
        if not eval_result.get("passes_threshold") or returncode != 0:

            result["messages"].append("Attempting fix...")

            fixer = BugFixerAgent()

            fix_result = fixer.fix_code(
                original_code=code,
                execution_result=exec_result,
                evaluation_result=eval_result
            )

            if fix_result.get("success") and fix_result.get("fixed_code"):

                current_code = fix_result["fixed_code"]

                result["messages"].append("Fix applied. Re-executing...")

                # Overwrite temp file with fixed code
                with open(code_path, "w", encoding="utf-8") as f:
                    f.write(current_code)

                stdout, stderr, returncode, exc = executor.execute_code_file(code_path)

                exec_result = {
                    "stdout": stdout,
                    "stderr": stderr,
                    "returncode": returncode,
                    "exception": exc
                }

                current_eval = evaluator.evaluate(
                    code=current_code,
                    task_description=task_description,
                    execution_result=exec_result
                )

                result["messages"].append(
                    f"After fix score: {current_eval.get('total_score')}"
                )

        # ---- FINAL DECISION ----

        if current_eval.get("passes_threshold"):

            result["messages"].append("Success — archiving & saving artifacts")

            archive = SolutionArchiveAgent()

            archive.archive_success(
                task_description=task_description,
                generated_code=current_code,
                evaluation_result=current_eval,
                metadata={"fixed": current_code != code}
            )

            artifact = ArtifactAgent()

            artifact.save_file("main.py", current_code)
            artifact.save_file(
                "evaluation.txt",
                str(current_eval),
                subfolder="logs"
            )

            build_path = artifact.get_build_path()
            result["build_path"] = str(build_path)

            result["messages"].append(
                f"Artifacts saved to: {result['build_path']}"
            )

        else:

            result["status"] = "failed"
            result["messages"].append(
                "Final score too low — no archive/artifacts"
            )

    finally:

        try:
            os.unlink(code_path)
        except Exception:
            pass

    return result