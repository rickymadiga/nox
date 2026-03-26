from typing import Dict, Any, List


class OutlineGeneratorJunior:

    async def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:

        topic = data.get("topic", "Topic")
        research = data.get("research", [])

        outline: List[str] = [
            f"1. Introduction to {topic}",
            f"2. Key Concepts of {topic}",
            f"3. How {topic} Works",
            f"4. Practical Applications",
            f"5. Common Mistakes",
            f"6. Conclusion"
        ]

        # If research exists, enhance outline slightly
        if research:
            outline.insert(3, f"4. Important Aspects of {topic}")

        return {
            "status": "ok",
            "outline": outline
        }