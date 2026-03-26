# forge/extensions/solution_archive_agent.py
"""
SolutionArchiveAgent – Append-only logger of successful builds.
Saves task description, generated code, evaluation score & metadata to a JSONL file.
This is an optional extension – always runs on success unless disabled in config.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class SolutionArchiveAgent:
    """
    Stores successful solutions for future learning / retrieval.
    Phase 1: simple JSONL append – no querying yet.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.archive_path = Path(self.config.get(
            "archive_path",
            "data/successful_solutions.jsonl"
        ))
        # Ensure parent directory exists
        self.archive_path.parent.mkdir(parents=True, exist_ok=True)

    def archive_success(
        self,
        task_description: str,
        generated_code: str,
        evaluation_result: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save a successful build to the archive.

        Args:
            task_description: The original user task
            generated_code: The final code string
            evaluation_result: Dict from EvaluatorAgent
            metadata: Optional extra info (timestamp auto-added)

        Returns:
            bool: True if saved successfully
        """
        timestamp = datetime.utcnow().isoformat()

        entry = {
            "timestamp": timestamp,
            "task": task_description.strip(),
            "code": generated_code.strip(),
            "evaluation": evaluation_result,
            "metadata": metadata or {}
        }

        try:
            with self.archive_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            print(f"[Archive] Saved successful solution at {timestamp}")
            return True
        except Exception as e:
            print(f"[Archive ERROR] Failed to save: {str(e)}")
            return False

    # Future: add query methods, RAG retrieval, pattern extraction, etc.