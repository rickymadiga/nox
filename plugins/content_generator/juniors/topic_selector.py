from typing import Dict, Any
import json
import ast


class TopicSelectorJunior:
    """
    Extracts and cleans topic text from many possible formats.
    Handles:
    - normal strings
    - dict objects
    - JSON strings
    - Python dict strings
    """

    async def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:

        topic = data.get("topic") or data.get("prompt") or "General Topic"

        # Case 1: topic is already a dict
        if isinstance(topic, dict):
            topic = topic.get("prompt", "")

        # Case 2: topic is a string that might contain JSON or Python dict
        if isinstance(topic, str):

            text = topic.strip()

            # Try JSON first
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    topic = parsed.get("prompt", text)
            except Exception:
                pass

            # Try Python dict string
            try:
                parsed = ast.literal_eval(text)
                if isinstance(parsed, dict):
                    topic = parsed.get("prompt", text)
            except Exception:
                pass

        topic = str(topic).strip()

        return {
            "status": "ok",
            "topic": topic
        }