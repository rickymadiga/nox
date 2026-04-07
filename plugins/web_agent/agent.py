import os
import httpx
import time
from typing import Dict, Any, List


class WebAgent:
    def __init__(self, name: str, bus: Any, context: dict):
        self.name = name
        self.bus = bus
        self.context = context
        self.runtime = None

        self.api_key = os.getenv("BRAVE_API_KEY")

        # 🔥 NEW: simple in-memory cache
        self.cache: Dict[str, Dict] = {}
        self.cache_ttl = 300  # 5 minutes

        # 🔥 NEW: rate limit
        self.last_calls: Dict[str, List[float]] = {}
        self.max_calls_per_user = 5

        if not self.api_key:
            print("[WebAgent] WARNING: Missing BRAVE_API_KEY")

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        query = task.get("query") or task.get("prompt")
        user_id = task.get("user_id", "default")

        if not query:
            return {"status": "error", "error": "No query provided"}

        # 🔒 RATE LIMIT
        if not self._allow_request(user_id):
            return {
                "status": "blocked",
                "error": "Search limit reached. Try later."
            }

        # ⚡ CACHE CHECK
        cached = self._get_cache(query)
        if cached:
            return {
                "status": "success",
                "query": query,
                "results": cached,
                "cached": True
            }

        try:
            results = await self._search_brave(query)

            # 💾 STORE CACHE
            self.cache[query] = {
                "data": results,
                "time": time.time()
            }

            return {
                "status": "success",
                "query": query,
                "results": results,
                "cached": False
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "query": query
            }

    # --------------------------------------------------
    # RATE LIMIT
    # --------------------------------------------------

    def _allow_request(self, user_id: str) -> bool:
        now = time.time()
        window = 60  # 1 minute

        calls = self.last_calls.get(user_id, [])
        calls = [t for t in calls if now - t < window]

        if len(calls) >= self.max_calls_per_user:
            return False

        calls.append(now)
        self.last_calls[user_id] = calls
        return True

    # --------------------------------------------------
    # CACHE
    # --------------------------------------------------

    def _get_cache(self, query: str):
        entry = self.cache.get(query)
        if not entry:
            return None

        if time.time() - entry["time"] > self.cache_ttl:
            return None

        return entry["data"]

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
    # PARSE + ENRICH
    # --------------------------------------------------

    def _parse_results(self, data: Dict[str, Any]) -> List[Dict[str, str]]:
        results = []

        web_results = data.get("web", {}).get("results", [])

        for item in web_results[:5]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("description", ""),
                # 🔥 NEW: short summary field for LLM
                "summary": (item.get("description", "")[:120] + "...")
            })

        return results