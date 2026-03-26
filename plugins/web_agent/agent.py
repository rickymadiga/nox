import os
import httpx
from typing import Dict, Any, List


class WebAgent:
    """
    Internet-enabled agent using Brave Search API.

    Returns structured results for other agents:
    - title
    - url
    - snippet
    """

    def __init__(self, name: str, bus: Any, context: dict):
        self.name = name
        self.bus = bus
        self.context = context
        self.runtime = None  # injected by runtime

        self.api_key = os.getenv("BRAVE_API_KEY")

        if not self.api_key:
            print("[WebAgent] WARNING: Missing BRAVE_API_KEY")

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        query = task.get("query") or task.get("prompt")

        if not query:
            return {"status": "error", "error": "No query provided"}

        try:
            results = await self._search_brave(query)

            return {
                "status": "success",
                "query": query,
                "results": results
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "query": query
            }

    # --------------------------------------------------
    # Brave Search
    # --------------------------------------------------

    async def _search_brave(self, query: str) -> List[Dict[str, str]]:
        url = "https://api.search.brave.com/res/v1/web/search"

        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key
        }

        params = {
            "q": query,
            "count": 5
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers, params=params)

            if response.status_code != 200:
                raise Exception(f"Brave API error: {response.status_code}")

            data = response.json()

        return self._parse_results(data)

    # --------------------------------------------------
    # Clean structured output
    # --------------------------------------------------

    def _parse_results(self, data: Dict[str, Any]) -> List[Dict[str, str]]:
        results = []

        web_results = data.get("web", {}).get("results", [])

        for item in web_results[:5]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("description", "")
            })

        return results