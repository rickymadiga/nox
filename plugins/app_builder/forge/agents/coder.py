# forge/agents/coder.py

import os
import json
import re
import asyncio
from typing import Any, Dict, Optional, List

from groq import AsyncGroq
from pydantic import BaseModel

from ..core.agent import Agent


# ────────────────────────────────────────────────
# Structured schema
# ────────────────────────────────────────────────

class GeneratedProject(BaseModel):
    files: Dict[str, str]


class Coder(Agent):
    """
    Coder Agent (DICT EVENT VERSION)

    • Receives PLAN_CREATED
    • Generates project files via LLM
    • Publishes CODE_GENERATED
    """

    MODEL = "llama-3.3-70b-versatile"

    def __init__(self, bus: Any, context: dict):
        super().__init__(name="coder", bus=bus, context=context)

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment")

        self.client = AsyncGroq(api_key=api_key)

    # ─────────────────────────────────────────────
    def register(self) -> None:
        print("[Coder] Subscribing → PLAN_CREATED")
        self.bus.subscribe("PLAN_CREATED", self.handle)

    # ─────────────────────────────────────────────
    async def handle(self, message: dict) -> None:
        if message.get("type") != "PLAN_CREATED":
            return

        payload = message.get("payload", {})

        task: str = payload.get("task", "").strip()
        plan_steps: List[str] = payload.get("plan", [])
        template: Optional[str] = payload.get("template")
        user_id: str = payload.get("user_id", "default_user")

        print(f"[Coder] Generating project → {task}")

        if not task:
            await self._publish_error("Empty task", payload)
            return

        plan_text = "\n".join(f"- {p}" for p in plan_steps) if plan_steps else "(no plan)"
        prompt = self._build_prompt(task, plan_text, template)

        files: Dict[str, str] = {}
        raw = ""

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

            print("[Coder] Raw output (first 400 chars):")
            print(raw[:400] + ("..." if len(raw) > 400 else ""))

            files = await self._parse_and_validate(raw, task, prompt)

        except asyncio.TimeoutError:
            print("[Coder] Model timeout")
            files = self._fallback_error_files(task, "Model timeout")

        except Exception as e:
            print(f"[Coder] Unexpected error: {e}")
            files = self.parse_file_blocks(raw) or self._fallback_error_files(task, str(e))

        # 🔥 PUBLISH DICT EVENT
        await self.bus.publish({
            "type": "CODE_GENERATED",
            "sender": self.name,
            "payload": {
                "files": files,
                "task": task,
                "template": template,
                "user_id": user_id
            }
        })

        print(f"[Coder] Sent CODE_GENERATED ({len(files)} files)")

    # ─────────────────────────────────────────────
    # FILE: Block Parser
    # ─────────────────────────────────────────────

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
            elif current_file is not None:
                buffer.append(line)

        if current_file and buffer:
            files[current_file] = "\n".join(buffer).strip()

        return files

    # ─────────────────────────────────────────────
    # Prompts
    # ─────────────────────────────────────────────

    def _system_prompt(self) -> str:
        return """
You are a professional Python developer.

Return ONLY a valid JSON object:

{
  "files": {
    "main.py": "code here"
  }
}

Rules:
- No explanations
- No markdown
- Always include main.py
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

        prompt += "\nGenerate full project. Return ONLY JSON."

        return prompt

    # ─────────────────────────────────────────────
    # JSON Helpers
    # ─────────────────────────────────────────────

    def _extract_json(self, text: str) -> str:
        start = text.find("{")
        end = text.rfind("}")
        return text[start:end + 1] if start != -1 and end != -1 else "{}"

    def _repair_llm_json(self, text: str) -> str:
        text = text.strip()
        text = re.sub(r"```json|```", "", text, flags=re.IGNORECASE)
        text = self._extract_json(text)
        text = re.sub(r",\s*([}\]])", r"\1", text)
        text = text.replace("\r", "")
        return text

    # ─────────────────────────────────────────────
    async def _parse_and_validate(self, raw: str, task: str, prompt: str) -> Dict[str, str]:
        for attempt in range(2):
            try:
                cleaned = self._repair_llm_json(raw)
                data = json.loads(cleaned)
                files = GeneratedProject.model_validate(data).files

                if "main.py" not in files:
                    raise ValueError("main.py missing")

                print("[Coder] JSON validated")
                return files

            except Exception as e:
                print(f"[Coder] JSON parse failed: {e}")

                if attempt == 0:
                    try:
                        retry = await self.client.chat.completions.create(
                            model=self.MODEL,
                            messages=[
                                {"role": "system", "content": self._system_prompt()},
                                {"role": "user", "content": prompt + "\nReturn ONLY JSON."},
                            ],
                            temperature=0.0,
                            max_tokens=12000,
                            response_format={"type": "json_object"},
                        )
                        raw = retry.choices[0].message.content.strip()
                    except Exception:
                        pass

        print("[Coder] Falling back to FILE parser")
        files = self.parse_file_blocks(raw)

        if files and "main.py" in files:
            return files

        return self._fallback_error_files(task, "Parsing failed")

    # ─────────────────────────────────────────────
    def _fallback_error_files(self, task: str, reason: str) -> Dict[str, str]:
        return {
            "main.py": f"""def main():
    print("Forge failed")
    print("Task: {task}")
    print("Reason: {reason}")

if __name__ == "__main__":
    main()
"""
        }

    # ─────────────────────────────────────────────
    async def _publish_error(self, reason: str, payload: Dict):
        await self.bus.publish({
            "type": "CODE_GENERATED",
            "sender": self.name,
            "payload": {
                **payload,
                "files": self._fallback_error_files("error", reason),
                "error": reason,
                "user_id": payload.get("user_id", "default_user")
            }
        })