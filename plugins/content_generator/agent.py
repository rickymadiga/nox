class ContentGeneratorAgent:

    def __init__(self, runtime):
        self.runtime = runtime


    async def run(self, task):

        # SAFE PROMPT EXTRACTION
        prompt = ""

        if isinstance(task, dict):
            prompt = task.get("prompt", "")
        else:
            prompt = getattr(task, "prompt", "")

        if not prompt:
            return {
                "agent": "content_generator",
                "error": "No prompt provided"
            }

        story = self.generate_story(prompt)

        return {
            "agent": "content_generator",
            "content": story
        }


    def generate_story(self, prompt):

        return f"""
Once upon a time in a world shaped by ideas, people constantly searched
for meaning in technology, nature, and creativity.

Your prompt was:
{prompt}

In this world, builders like you created intelligent systems that could
understand humans, assist with daily life, and evolve with time.

And that was only the beginning of the story.
"""