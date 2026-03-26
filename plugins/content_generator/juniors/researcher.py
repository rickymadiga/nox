from typing import Dict, Any


class ResearchJunior:

    async def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:

        topic = data.get("topic", "Topic")

        research_points = [
            f"What {topic} is",
            f"Why {topic} is important",
            f"How {topic} works",
            f"Tools used in {topic}",
            f"Real world examples of {topic}"
        ]

        return {
            "status": "ok",
            "research": research_points
        }