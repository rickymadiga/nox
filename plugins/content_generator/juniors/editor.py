from typing import Dict, Any


class EditorJunior:

    async def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:

        content = data.get("content", "")

        # simple formatting cleanup
        edited = content.replace("  ", " ").strip()

        return {
            "status": "ok",
            "edited_content": edited
        }