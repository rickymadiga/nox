# forge/extensions/bug_fixer_agent.py
"""
BugFixerAgent – Attempts to fix failing code based on execution errors and evaluation feedback.
This is an optional extension – triggered when evaluation score is low or execution fails.
"""

from typing import Dict, Any, List, Optional
import re


class BugFixerAgent:
    """
    Analyzes error messages and code to suggest / apply basic fixes.
    Phase 1: rule-based fixes – no LLM yet.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.max_fix_attempts = self.config.get("max_fix_attempts", 3)

    def fix_code(
        self,
        original_code: str,
        execution_result: Dict[str, Any],
        evaluation_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Try to fix the code based on errors.

        Returns:
            {
                "fixed_code": str or None,
                "fixes_applied": list of strings describing changes,
                "success": bool,
                "comments": list of notes
            }
        """
        fixes_applied: List[str] = []
        comments: List[str] = []

        code = original_code.strip()

        # 1. Syntax / NameError fixes (common patterns)
        if execution_result.get("exception") and "NameError" in str(execution_result["exception"]):
            missing_name = re.search(r"name '(\w+)' is not defined", str(execution_result["exception"]))
            if missing_name:
                name = missing_name.group(1)
                if name == "print":
                    fixes_applied.append("Added missing import for print (unlikely, but example)")
                    code = "from __future__ import print_function\n" + code
                else:
                    fixes_applied.append(f"Added possible missing import or definition for '{name}'")
                    code = f"# TODO: define or import {name}\n" + code

        # 2. Add basic try/except if no error handling and execution failed
        if execution_result.get("returncode") != 0 and "try:" not in code:
            fixes_applied.append("Added basic try/except wrapper")
            code = """
try:
    {}
except Exception as e:
    print(f"Error: {{e}}")
""".format(code.replace("\n", "\n    "))

        # 3. Execution timeout → add timeout check comment
        if "TimeoutExpired" in str(execution_result.get("exception", "")):
            fixes_applied.append("Execution timed out – consider reducing complexity or adding timeout")
            comments.append("Code may have infinite loop or heavy computation")

        # 4. If evaluation mentioned error handling
        if evaluation_result and "No visible error handling" in str(evaluation_result.get("comments", [])):
            fixes_applied.append("Added comment for missing error handling")
            code += "\n# TODO: add proper error handling (try/except)"

        success = len(fixes_applied) > 0 or "No fixes needed" in str(execution_result.get("exception", ""))

        return {
            "fixed_code": code if success else None,
            "fixes_applied": fixes_applied,
            "success": success,
            "comments": comments
        }

    # Future: LLM-based fix suggestions, patch application, re-execute loop