# nox/assistant/lily.py
from nox.core.capability_registry import CapabilityRegistry
from typing import Dict
from groq import Groq


class Lily:
    """
    Lily - NOX Assistant

    Converts natural language prompts into structured NOX tasks.
    """

    MODEL = "llama-3.3-70b-versatile"

    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
        self.registry = CapabilityRegistry()
        self.registry.load()

    def understand(self, prompt: str):

        plugin = self.registry.find_plugin_for_prompt(prompt)

        if not plugin:
            return {
                "plugin": "assistant",
                "task": "conversation",
                "input": prompt
            }   

    def understand(self, prompt: str) -> Dict:
        """
        Convert a user prompt into a structured NOX task.
        """

        system_prompt = """
You are Lily, the assistant for the NOX AI system.

Convert the user's request into a structured JSON task.

Plugins available:

app_builder → builds software projects
analyzer → analyzes datasets and creates charts

Return JSON only:

{
 "plugin": "...",
 "task": "...",
 "input": "original user request"
}
"""

        response = self.client.chat.completions.create(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )

        text = response.choices[0].message.content.strip()

        import json
        return json.loads(text)