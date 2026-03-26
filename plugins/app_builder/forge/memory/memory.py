import json
import os
from typing import Dict, List

from ..core.message import Message


class Memory:
    """
    Forge long-term memory.

    Learns from reviewer feedback and stores recurring bug patterns.
    """

    def __init__(self, name, bus, context):

        self.name = name
        self.bus = bus
        self.context = context

        self.memory_file = "forge/memory/knowledge.json"

        self.knowledge = self.load_memory()

    # ----------------------------------
    # REGISTRATION
    # ----------------------------------

    def register(self):

        self.bus.subscribe("REVIEW_COMPLETED", self.learn_from_review)

    # ----------------------------------
    # LOAD MEMORY
    # ----------------------------------

    def load_memory(self) -> Dict:

        if not os.path.exists(self.memory_file):
            return {
                "bugs": [],
                "stats": {}
            }

        try:
            with open(self.memory_file, "r") as f:
                return json.load(f)

        except Exception:

            print("[Memory] Memory file corrupted, resetting")

            return {
                "bugs": [],
                "stats": {}
            }

    # ----------------------------------
    # SAVE MEMORY
    # ----------------------------------

    def save_memory(self):

        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)

        with open(self.memory_file, "w") as f:
            json.dump(self.knowledge, f, indent=4)

    # ----------------------------------
    # LEARN FROM REVIEW
    # ----------------------------------

    async def learn_from_review(self, message: Message):

        print("[Memory] Learning from review")

        payload = message.payload or {}

        review = payload.get("review", {})

        issues: List[str] = review.get("issues", [])

        learned = 0

        for issue in issues:

            if not self.issue_known(issue):

                fix_type = self.classify_issue(issue)

                entry = {
                    "issue": issue,
                    "fix": fix_type
                }

                self.knowledge["bugs"].append(entry)

                learned += 1

                print(f"[Memory] Learned issue → {issue}")

        if learned:
            self.save_memory()

    # ----------------------------------
    # ISSUE CHECK
    # ----------------------------------

    def issue_known(self, issue: str) -> bool:

        for bug in self.knowledge["bugs"]:

            if bug["issue"] == issue:
                return True

        return False

    # ----------------------------------
    # CLASSIFY BUG TYPE
    # ----------------------------------

        def classify_issue(self, issue: str) -> str:
         """
        Simple rule-based classification of common code review issues.
        Will be extended over time based on real feedback.
        """
        text = issue.lower().strip()

        if "unused" in text and ("import" in text or "variable" in text):
            return "remove_unused"

        if any(x in text for x in ["undefined name", "nameerror", "not defined"]):
            return "fix_name_error"

        if any(x in text for x in ["indentationerror", "unexpected indent", "unindent does not match"]):
            return "fix_indentation"

        if "syntax" in text or "invalid syntax" in text:
            return "repair_syntax"

        if any(x in text for x in ["module not found", "importerror", "no module named"]):
            return "fix_import"

        if "attributeerror" in text and "has no attribute" in text:
            return "fix_attribute_error"

        return "other"