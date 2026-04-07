class ChatAgent:
    """
    General conversation / explanation agent.
    Handles prompts that are not tool-specific.
    """

    def __init__(self, runtime):
        self.runtime = runtime


    async def run(self, task):

        prompt = task.get("prompt", "")

        # Simple intelligent fallback responses
        # Later you can plug an LLM here

        if "space" in prompt.lower():
            return {
                "agent": "chat",
                "message": "Space is the vast region beyond Earth's atmosphere containing planets, stars, galaxies, and cosmic phenomena."
            }

        if "machine learning" in prompt.lower():
            return {
                "agent": "chat",
                "message": "Machine learning is a field of artificial intelligence where computers learn patterns from data to make predictions or decisions."
            }

        return {
            "agent": "chat",
            "message": "That's an interesting question. I'm still learning, but I can help explain many topics."
        }