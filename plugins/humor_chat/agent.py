class HumorAgent:

    def __init__(self, runtime):
        self.runtime = runtime

    async def run(self, task):

        jokes = [
            "Why do programmers hate nature? Too many bugs.",
            "Why did Python go to therapy? Too many unresolved imports.",
            "Why did the AI cross the road? To optimize the other side."
        ]

        import random

        return {
            "humor": random.choice(jokes)
        }