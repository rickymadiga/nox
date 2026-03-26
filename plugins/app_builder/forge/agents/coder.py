# forge/agents/coder.py

import os
import json
import re
import asyncio
from typing import Any, Dict, Optional, List

from groq import AsyncGroq
from pydantic import BaseModel, ValidationError

from ..core.agent import Agent
from ..core.message import Message


# ────────────────────────────────────────────────
# Structured schema
# ────────────────────────────────────────────────

class GeneratedProject(BaseModel):
    files: Dict[str, str]


class Coder(Agent):
    """
    Coder Agent

    • Receives PLAN_CREATED
    • Attempts structured JSON output
    • Falls back to FILE: block parsing if JSON fails
    • Publishes CODE_GENERATED
    """

    MODEL = "llama-3.3-70b-versatile"

    def __init__(self, name: str, bus: Any, context: dict):
        super().__init__(name=name, bus=bus, context=context)

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment")

        self.client = AsyncGroq(api_key=api_key)

    def register(self) -> None:
        print("[Coder] Subscribing → PLAN_CREATED")
        self.bus.subscribe("PLAN_CREATED", self.handle)

    async def handle(self, message: Message) -> None:
        if message.message_type != "PLAN_CREATED":
            return

        payload = message.payload or {}
        task: str = payload.get("task", "").strip()
        plan_steps: List[str] = payload.get("plan", [])
        template: Optional[str] = payload.get("template")

        print(f"[Coder] Generating project → {task}")

        if not task:
            await self._publish_error("Empty task", {})
            return

        plan_text = "\n".join(f"- {p}" for p in plan_steps) if plan_steps else "(no plan)"

        prompt = self._build_prompt(task, plan_text, template)

        files: Dict[str, str] = {}

        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.MODEL,
                    messages=[
                        {"role": "system", "content": self._system_prompt()},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.15,
                    max_tokens=12000,
                    response_format={"type": "json_object"},
                ),
                timeout=90,
            )

            raw = response.choices[0].message.content.strip()
            print("[Coder] Raw model output received (first 400 chars):")
            print(raw[:400] + ("..." if len(raw) > 400 else ""))

            files = await self._parse_and_validate(raw, task, prompt)

        except asyncio.TimeoutError:
            print("[Coder] Model timeout")
            files = self._fallback_error_files(task, "Model timeout")

        except Exception as e:
            print(f"[Coder] Unexpected error: {e}")
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
                },
            )
        )

        print(f"[Coder] Sent CODE_GENERATED ({len(files)} files)")

    # ────────────────────────────────────────────────
    # FILE: Block Parser (Added as requested)
    # ────────────────────────────────────────────────

    def parse_file_blocks(self, text: str) -> Dict[str, str]:
        """Parse output that uses FILE: filename format"""
        files: Dict[str, str] = {}

        current_file = None
        buffer: List[str] = []

        for line in text.splitlines():
            if line.startswith("FILE:"):
                if current_file and buffer:
                    files[current_file] = "\n".join(buffer).strip()

                current_file = line.replace("FILE:", "").strip()
                buffer = []
            elif current_file is not None:
                buffer.append(line)

        if current_file and buffer:
            files[current_file] = "\n".join(buffer).strip()

        return files

    # ────────────────────────────────────────────────
    # Prompts
    # ────────────────────────────────────────────────

    def _system_prompt(self) -> str:
        return """
You are a professional Python developer.

Return ONLY a valid JSON object using this exact schema:

{
  "files": {
    "main.py": "full python code here",
    "utils.py": "other file content"
  }
}

Rules:
- Output must be valid JSON only. No explanations, no markdown, no backticks.
- Always include "main.py"
- Escape quotes as \\" and newlines as \\n inside strings.
"""

    def _build_prompt(self, task: str, plan: str, template: Optional[str]) -> str:
        prompt = f"""
TASK:
{task}

PLAN:
{plan}
"""
        if template:
            prompt += f"\nUse template: {template}"

        prompt += """

Generate a complete runnable multi-file Python project.
Return ONLY the JSON object matching the schema above.
Do not write any text outside the JSON.
"""
        return prompt

    # ────────────────────────────────────────────────
    # JSON Helpers
    # ────────────────────────────────────────────────

    def _extract_json(self, text: str) -> str:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return "{}"
        return text[start:end + 1]

    def _repair_llm_json(self, text: str) -> str:
        text = text.strip()
        text = re.sub(r"```json|```", "", text, flags=re.IGNORECASE)
        text = self._extract_json(text)
        text = re.sub(r",\s*([}\]])", r"\1", text)   # remove trailing commas
        text = text.replace("\r", "")
        return text

    # ────────────────────────────────────────────────
    # Parse + Validation with fallback
    # ────────────────────────────────────────────────

    async def _parse_and_validate(self, raw: str, task: str, prompt: str) -> Dict[str, str]:
        # Try JSON first
        for attempt in range(2):
            try:
                cleaned = self._repair_llm_json(raw)
                data = json.loads(cleaned)
                validated = GeneratedProject.model_validate(data)
                files = validated.files

                if "main.py" not in files:
                    raise ValueError("main.py is missing")

                print("[Coder] JSON validated successfully")
                return files

            except Exception as e:
                print(f"[Coder] JSON parse failed attempt {attempt+1}: {e}")

                if attempt == 0:
                    # Retry with stronger instruction
                    try:
                        retry = await self.client.chat.completions.create(
                            model=self.MODEL,
                            messages=[
                                {"role": "system", "content": self._system_prompt()},
                                {"role": "user", "content": prompt + "\n\nReturn ONLY valid JSON. No other text."},
                            ],
                            temperature=0.0,
                            max_tokens=12000,
                            response_format={"type": "json_object"},
                        )
                        raw = retry.choices[0].message.content.strip()
                    except Exception as retry_err:
                        print(f"[Coder] Retry failed: {retry_err}")

        # Final fallback: Try parsing as FILE: blocks
        print("[Coder] Falling back to FILE: block parser")
        files = self.parse_file_blocks(raw)
        if files and "main.py" in files:
            print(f"[Coder] Recovered {len(files)} files using FILE: parser")
            return files

        # Ultimate fallback
        return self._fallback_error_files(task, "Both JSON and block parsing failed")

    # ────────────────────────────────────────────────
    # Fallback
    # ────────────────────────────────────────────────

    def _fallback_error_files(self, task: str, reason: str) -> Dict[str, str]:
        code = f'''def main():
    print("Forge failed to generate project")
    print("Task: {task}")
    print("Reason: {reason}")

if __name__ == "__main__":
    main()
'''
        return {"main.py": code}

    async def _publish_error(self, reason: str, payload: Dict):
        await self.bus.publish(
            Message(
                sender=self.name,
                recipient="tester",
                message_type="CODE_GENERATED",
                payload={
                    **payload,
                    "files": self._fallback_error_files("error", reason),
                    "error": reason,
                },
            )
        )