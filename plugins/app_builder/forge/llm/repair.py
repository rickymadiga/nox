# forge/llm/repair.py

from typing import List, Optional
import os

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class LLMRepair:
    """
    LLM-powered code repair engine
    """

    def __init__(self, client: Optional[object] = None):
        """
        Accepts external client OR creates one automatically
        """
        if client:
            self.client = client
        else:
            if OpenAI is None:
                raise ImportError("openai package not installed")

            api_key = os.getenv("OPENAI_API_KEY")

            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")

            self.client = OpenAI(api_key=api_key)

    async def fix(
        self,
        code: str,
        issues: List[str],
        test_errors: List[str],
        task: str = ""
    ) -> str:
        """
        Sends code + issues to LLM and gets a fixed version
        """

        issues_text = "\n".join(issues) if issues else "None"
        errors_text = "\n".join(test_errors) if test_errors else "None"

        prompt = f"""
You are an expert Python code repair AI.

Your job:
Fix the provided code based on issues and runtime errors.

STRICT RULES:
- Return ONLY valid Python code
- NO explanations
- NO markdown
- NO ``` blocks
- Keep the structure unless necessary
- Fix ALL errors

TASK:
{task}

ISSUES:
{issues_text}

RUNTIME ERRORS:
{errors_text}

CODE:
{code}

FIXED CODE:
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",   # fast + cheap + good
                messages=[
                    {"role": "system", "content": "You fix broken Python code."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )

            fixed_code = response.choices[0].message.content

            if not fixed_code:
                return code

            # Safety cleanup
            fixed_code = fixed_code.strip()

            return fixed_code

        except Exception as e:
            print(f"[LLMRepair] Error: {e}")
            return code