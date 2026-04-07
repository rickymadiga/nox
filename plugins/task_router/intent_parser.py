"""
Intent Parser

Responsible for:
- Normalizing incoming user requests
- Extracting the main prompt text
- Providing structured intent data to the RouterAgent
"""

from typing import Any, Dict


class IntentParser:
    """
    Converts raw input into a normalized intent structure.
    """

    def parse(self, intent: Any) -> Dict[str, Any]:
        """
        Parse incoming intent (string or dict) and return structured data.
        """

        if isinstance(intent, dict):
            prompt = intent.get("prompt", "")
            user = intent.get("user", "anonymous")
            metadata = intent.get("metadata", {})

        else:
            prompt = str(intent)
            user = "anonymous"
            metadata = {}

        normalized_prompt = self._normalize(prompt)

        return {
            "prompt": normalized_prompt,
            "user": user,
            "metadata": metadata,
            "raw_prompt": prompt
        }

    def _normalize(self, text: str) -> str:
        """
        Normalize text for routing analysis.
        """

        return text.strip().lower()