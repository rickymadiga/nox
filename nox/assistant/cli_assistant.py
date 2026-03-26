# nox/assistant/cli_assistant.py

import os
from nox.assistant.lily import Lily


class CLIAssistant:
    """
    CLI interface for NOX.
    """

    def __init__(self, engine):
        self.engine = engine
        api_key = os.getenv("GROQ_API_KEY")
        self.lily = Lily(api_key)

    def run(self):

        print("\n🧠 NOX Assistant (CLI)")
        print("Type 'exit' to quit\n")

        while True:

            prompt = input("You > ").strip()

            if prompt.lower() in ["exit", "quit"]:
                break

            try:

                task = self.lily.understand(prompt)

                print("\n[Lily parsed task]")
                print(task)

                result = self.engine.handle_task(task)

                print("\n[NOX RESULT]")
                print(result)

            except Exception as e:
                print("Error:", e)