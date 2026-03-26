from datetime import datetime


class AnalyticsAgent:
    """
    Tracks simple usage analytics for NOX
    """

    def __init__(self, runtime):
        self.runtime = runtime
        self.events = []

    async def run(self, task):

        # Safe prompt extraction
        prompt = str(task.get("prompt", ""))
        text = prompt.lower()

        # Request analytics stats
        if "analytics" in text or "stats" in text:

            return {
                "agent": "analytics",
                "tracked_events": len(self.events),
                "message": f"Tracked events: {len(self.events)}"
            }

        # Track prompt usage
        event = {
            "prompt": prompt,
            "time": datetime.utcnow().isoformat()
        }

        self.events.append(event)

        return {
            "agent": "analytics",
            "message": "Event recorded."
        }