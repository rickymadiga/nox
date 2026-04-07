# forge/agents/coder.py

import os
import json
import re
import asyncio
from typing import Any, Dict, Optional, List

from groq import AsyncGroq
from pydantic import BaseModel

from ..core.agent import Agent
from ..core.message import Message


# ────────────────────────────────────────────────
# Structured schema
# ────────────────────────────────────────────────

class GeneratedProject(BaseModel):
    files: Dict[str, str]


class Coder(Agent):

    MODEL = "llama-3.3-70b-versatile"

    # 🔥 HARD LIMIT CONFIG
    MAX_INPUT_TOKENS = 6000   # safe input
    MAX_OUTPUT_TOKENS = 4000  # safe output

    def __init__(self, name: str, bus: Any, context: dict):
        super().__init__(name=name, bus=bus, context=context)

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found")

        self.client = AsyncGroq(api_key=api_key)

    def register(self) -> None:
        print("[Coder] Subscribing → PLAN_CREATED")
        self.bus.subscribe("PLAN_CREATED", self.handle)

    # ────────────────────────────────────────────────
    # 🔥 SAFE TRUNCATION
    # ────────────────────────────────────────────────
    def _truncate(self, text: str, max_tokens: int = 6000) -> str:
        max_chars = max_tokens * 4  # rough conversion
        return text[:max_chars]

    # ────────────────────────────────────────────────
    async def handle(self, message: Message) -> None:
        if message.message_type != "PLAN_CREATED":
            return

        payload = message.payload or {}
        task: str = payload.get("task", "").strip()
        plan_steps: List[str] = payload.get("plan", [])
        template: Optional[str] = payload.get("template")

        # Added by user
        user_id = payload.get("user_id", "default_user")
        fix_attempts = payload.get("fix_attempts", 0)

        print(f"[Coder] Generating project → {task}")

        if not task:
            await self._publish_error("Empty task", {})
            return

        # 🔥 LIMIT PLAN SIZE
        plan_text = "\n".join(f"- {p}" for p in plan_steps[:20])

        prompt = self._build_prompt(task, plan_text, template)

        # 🔥 HARD LIMIT PROMPT
        prompt = self._truncate(prompt, self.MAX_INPUT_TOKENS)

        files: Dict[str, str] = {}
        raw = ""  # 🔥 FIX: ensure defined

        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.MODEL,
                    messages=[
                        {"role": "system", "content": self._system_prompt()},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.15,
                    max_tokens=self.MAX_OUTPUT_TOKENS,
                    response_format={"type": "json_object"},
                ),
                timeout=90,
            )

            raw = response.choices[0].message.content.strip()

            print("[Coder] Raw output (first 300 chars):")
            print(raw[:300])

            files = await self._parse_and_validate(raw, task, prompt, template)

        except Exception as e:
            print(f"[Coder] ERROR: {e}")

            # 🔥 RETRY WITH SMALLER PROMPT
            try:
                print("[Coder] Retrying with smaller prompt...")
                smaller_prompt = self._truncate(prompt, 3000)

                response = await self.client.chat.completions.create(
                    model=self.MODEL,
                    messages=[
                        {"role": "system", "content": self._system_prompt()},
                        {"role": "user", "content": smaller_prompt},
                    ],
                    temperature=0.1,
                    max_tokens=2000,
                    response_format={"type": "json_object"},
                )

                raw = response.choices[0].message.content.strip()
                files = await self._parse_and_validate(raw, task, smaller_prompt, template)

            except Exception as retry_err:
                print(f"[Coder] Retry failed: {retry_err}")
                files = self.parse_file_blocks(raw) or self._fallback_error_files(task, str(e))

        await self.bus.publish(
            Message(
                sender=self.name,
                recipient="tester",
                message_type="CODE_GENERATED",
                payload={
                    "files": files,
                    "task": task,
                    "template": template,
                    "user_id": user_id,
                    "fix_attempts": fix_attempts,
                },
            )
        )

        print(f"[Coder] Sent CODE_GENERATED ({len(files)} files)")

    # ────────────────────────────────────────────────
    def parse_file_blocks(self, text: str) -> Dict[str, str]:
        files: Dict[str, str] = {}
        current_file = None
        buffer: List[str] = []

        for line in text.splitlines():
            if line.startswith("FILE:"):
                if current_file and buffer:
                    files[current_file] = "\n".join(buffer).strip()
                current_file = line.replace("FILE:", "").strip()
                buffer = []
            elif current_file:
                buffer.append(line)

        if current_file and buffer:
            files[current_file] = "\n".join(buffer).strip()

        return files

    # ────────────────────────────────────────────────
    def _system_prompt(self) -> str:
        return """
You are a senior Python developer.

Return ONLY JSON:

{
  "files": {
    "main.py": "code",
    "requirements.txt": "dependencies"
  }
}

Rules:
- Always include BOTH main.py AND requirements.txt
- main.py must be runnable
- requirements.txt must include all dependencies
- No explanations, no markdown
"""

    def _build_prompt(self, task: str, plan: str, template: Optional[str]) -> str:
        template_hint = ""

        if template == "streamlit":
            template_hint = """
- MUST use Streamlit
- MUST include st.button to trigger computation
- MUST display result using st.write
"""
        elif template == "fastapi":
            template_hint = """
- MUST use FastAPI
- MUST include at least one endpoint
"""
        else:
            template_hint = """
- Must be a CLI Python script
"""

        return f"""
TASK:
{task}

PLAN:
{plan}

REQUIREMENTS:
{template_hint}

Generate a minimal working Python project.
Return ONLY JSON.
"""

    # ────────────────────────────────────────────────
    def _extract_json(self, text: str) -> str:
        start = text.find("{")
        end = text.rfind("}")
        return text[start:end + 1] if start != -1 and end != -1 else "{}"

    def _repair_llm_json(self, text: str) -> str:
        text = re.sub(r"```json|```", "", text, flags=re.IGNORECASE)
        text = self._extract_json(text)
        text = re.sub(r",\s*([}\]])", r"\1", text)
        return text

    # ────────────────────────────────────────────────
    async def _parse_and_validate(self, raw: str, task: str, prompt: str, template: Optional[str]) -> Dict[str, str]:
        try:
            cleaned = self._repair_llm_json(raw)
            data = json.loads(cleaned)
            validated = GeneratedProject.model_validate(data)
            files = validated.files

            # Add missing requirements.txt based on template
            if "requirements.txt" not in files:
                if template == "streamlit":
                    files["requirements.txt"] = "streamlit\n"
                elif template == "fastapi":
                    files["requirements.txt"] = "fastapi\nuvicorn\n"
                else:
                    files["requirements.txt"] = ""

            return files

        except Exception as e:
            print(f"[Coder] JSON failed: {e}")
            return self.parse_file_blocks(raw) or self._fallback_error_files(task, str(e))

    # ────────────────────────────────────────────────
    def _fallback_error_files(self, task: str, reason: str) -> Dict[str, str]:
        return {
            "main.py": f'''
import streamlit as st

st.title("Build Failed ⚠️")

st.error("Task: {task}")
st.error("Reason: {reason}")

if st.button("Retry"):
    st.write("Please try again.")
''',
            "requirements.txt": "streamlit\n"
        }

    async def _publish_error(self, reason: str, payload: Dict):
        await self.bus.publish(
            Message(
                sender=self.name,
                recipient="tester",
                message_type="CODE_GENERATED",
                payload={
                    **payload,
                    "files": self._fallback_error_files("error", reason),
                },
            )
        )