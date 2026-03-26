from typing import Dict, Any


class QualityReviewerJunior:

    async def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:

        content = data.get("content", "")

        score = 80

        if len(content) > 800:
            score = 90

        return {
            "status": "ok",
            "quality_score": score,
            "approved": score >= 70
        }