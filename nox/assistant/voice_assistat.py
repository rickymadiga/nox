# nox/assistant/voice_assistant.py

import os
import speech_recognition as sr

from nox.assistant.lily import Lily


class VoiceAssistant:
    """
    Voice interface for NOX.
    """

    def __init__(self, engine):
        api_key = os.getenv("GROQ_API_KEY")
        self.lily = Lily(api_key)
        self.engine = engine
        self.recognizer = sr.Recognizer()

    def listen(self):

        with sr.Microphone() as source:

            print("🎤 Listening...")
            audio = self.recognizer.listen(source)

        try:

            text = self.recognizer.recognize_google(audio)
            print("You said:", text)

            task = self.lily.understand(text)

            print("[Parsed Task]", task)

            result = self.engine.handle_task(task)

            print("[Result]", result)

        except Exception as e:
            print("Voice error:", e)