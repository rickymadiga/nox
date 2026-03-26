import requests
from datetime import datetime

class AnalyticsAgent:
    def __init__(self):
        print("[analytics] AnalyticsAgent initialized")

    def process(self, task):
        """
        Main entry point. Expects task.prompt containing the query (e.g. "bitcoin price", "population of Kenya").
        Returns consistent success/error format matching other agents.
        """
        prompt = task.prompt.lower().strip()

        if not prompt:
            return {
                "status": "error",
                "message": "No analytics query provided"
            }

        # Very simple keyword-based topic/entity extraction
        topic = "bitcoin"  # sensible default fallback
        indicators = [
            "price of", "value of", "how much is", "cost of",
            "population of", "how many people in", "population in",
            "stats for", "statistics on", "data on", "number of"
        ]

        for indicator in indicators:
            if indicator in prompt:
                parts = prompt.split(indicator, 1)
                if len(parts) > 1:
                    remaining = parts[1].strip().split()
                    if remaining:
                        topic_candidate = remaining[0].rstrip(",.;!?")
                        if topic_candidate:
                            topic = topic_candidate
                            break

        # Route to specific handler based on detected topic
        if any(kw in topic for kw in ["bitcoin", "btc", "ethereum", "eth", "solana", "crypto"]):
            return self._fetch_crypto_price(topic)

        elif any(kw in topic for kw in ["population", "people in", "population of"]):
            return self._fetch_population(topic)

        else:
            # Fallback: try to get any quick fact / statistic via DuckDuckGo
            return self._fetch_general_statistic(prompt)

    def _fetch_crypto_price(self, coin):
        try:
            # CoinGecko free public API – no key required
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd,eur"
            response = requests.get(url, timeout=8)
            response.raise_for_status()

            data = response.json()
            if coin not in data or "usd" not in data[coin]:
                return {
                    "status": "error",
                    "message": f"No price data available for '{coin}'"
                }

            usd_price = data[coin]["usd"]
            eur_price = data[coin].get("eur", "—")

            result = {
                "entity": coin.upper(),
                "metric": "current_price",
                "value_usd": f"${usd_price:,.2f}",
                "value_eur": f"€{eur_price:,.2f}" if eur_price != "—" else "—",
                "source": "CoinGecko",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            return {
                "status": "success",
                "analytics": result
            }

        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "message": f"HTTP {e.response.status_code if e.response else 'unknown'}: {coin}"
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "message": "Crypto price service timed out — try again later"
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "message": f"Network error: {str(e)}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}"
            }

    def _fetch_population(self, place):
        try:
            # Using DuckDuckGo instant answer for population
            url = "https://api.duckduckgo.com/"
            params = {
                "q": f"population of {place}",
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1
            }
            response = requests.get(url, params=params, timeout=8)
            response.raise_for_status()

            data = response.json()
            abstract = data.get("Abstract", "").strip()

            if not abstract:
                return {
                    "status": "error",
                    "message": f"No population information found for '{place}'"
                }

            result = {
                "entity": place.title(),
                "metric": "population",
                "value": abstract,
                "source": data.get("AbstractSource", "DuckDuckGo"),
                "url": data.get("AbstractURL", "")
            }

            return {
                "status": "success",
                "analytics": result
            }

        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "message": "Population lookup timed out — try again later"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error fetching population data: {str(e)}"
            }

    def _fetch_general_statistic(self, query):
        try:
            url = "https://api.duckduckgo.com/"
            params = {
                "q": f"{query} statistics OR number OR data",
                "format": "json",
                "no_html": 1
            }
            response = requests.get(url, params=params, timeout=8)
            response.raise_for_status()

            data = response.json()
            abstract = data.get("Abstract", "").strip() or "No quick statistic available."

            result = {
                "entity": query.title(),
                "metric": "quick_fact",
                "value": abstract,
                "source": data.get("AbstractSource", "DuckDuckGo"),
                "url": data.get("AbstractURL", "")
            }

            return {
                "status": "success",
                "analytics": result
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"General statistic lookup failed: {str(e)}"
            }