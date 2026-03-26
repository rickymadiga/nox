import os
import requests

class LLMService:

    def __init__(self):

        self.groq_key = os.getenv("GROQ_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")

    def generate(self, prompt):

        # -------------------
        # Try GROQ
        # -------------------

        if self.groq_key:
            try:
                print("[LLM] Trying Groq")

                r = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.groq_key}"
                    },
                    json={
                        "model": "llama3-70b-8192",
                        "messages": [
                            {"role": "user", "content": prompt}
                        ]
                    }
                )

                return r.json()["choices"][0]["message"]["content"]

            except Exception as e:
                print("[LLM] Groq failed:", e)

        # -------------------
        # Try OpenAI
        # -------------------

        if self.openai_key:
            try:
                print("[LLM] Trying OpenAI")

                r = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_key}"
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "user", "content": prompt}
                        ]
                    }
                )

                return r.json()["choices"][0]["message"]["content"]

            except Exception as e:
                print("[LLM] OpenAI failed:", e)

        raise Exception("No working LLM provider found")