from typing import Dict, Any, List


class SEOOptimizerJunior:

    async def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:

        topic = data.get("topic", "Article")
        content = data.get("content", "")

        # Basic keyword extraction
        keywords: List[str] = []

        topic_words = topic.lower().split()

        for word in topic_words:
            if len(word) > 3:
                keywords.append(word)

        if not keywords:
            keywords.append(topic.lower())

        seo = {
            "title": f"{topic} - Complete Guide",
            "meta_description": f"Learn everything about {topic}. A clear and practical guide covering concepts, implementation, and best practices.",
            "keywords": keywords
        }

        return {
            "status": "ok",
            "seo": seo
        }