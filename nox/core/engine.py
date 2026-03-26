# lily_brain.py — NOX HYBRID BRAIN (v4 GOD-AWARE)

import json
import os
import re
import time
import requests
from collections import defaultdict
from typing import Dict, Any


class Engine:
    def __init__(self, user_name: str):
        self.user_name = user_name

        # 🧠 IDENTITY (NEW — SELF AWARE ROLE)
        self.role = "orchestrator"
        self.capabilities = [
            "respond",
            "delegate",
            "orchestrate",
            "learn",
            "recall",
            "fix_code"
        ]

        # -------------------------
        # MEMORY (lightweight + decay)
        # -------------------------
        self.memory = defaultdict(int)
        self.last_seen = {}

        # -------------------------
        # LLM (optional)
        # -------------------------
        self.openai = None
        self.ollama_url = "http://localhost:11434/api/generate"

        self._init_models()

        # -------------------------
        # TOOLS (EXECUTION LAYER)
        # -------------------------
        self.tools = {
            "learn": self.tool_learn,
            "recall": self.tool_recall,
            "chat": self.tool_chat,
            "fix_code": self.tool_fix_code,
        }

    # =================================================
    # INIT MODELS
    # =================================================
    def _init_models(self):
        try:
            if os.getenv("OPENAI_API_KEY"):
                from openai import OpenAI
                self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                print("[Lily] OpenAI ✓")
        except:
            pass

        try:
            requests.get("http://localhost:11434")
            print("[Lily] Ollama ✓")
        except:
            pass

    # =================================================
    # MEMORY SYSTEM
    # =================================================
    def _normalize(self, text: str):
        return re.sub(r"[^a-z0-9\s]", "", text.lower()).strip()

    def decay_memory(self):
        now = time.time()
        for k in list(self.memory.keys()):
            age = now - self.last_seen.get(k, now)

            if age > 86400:
                self.memory[k] *= 0.9

            if self.memory[k] < 0.5:
                del self.memory[k]

    # =================================================
    # 🧠 ROLE AWARE DECISION ENGINE (UPGRADED — TRUE ORCHESTRATOR)
    # =================================================
    def decide_role_action(self, intent: Dict[str, Any], user_input: str) -> Dict[str, Any]:
        """
        Lily's TRUE ROLE:
        1. Answer directly if simple
        2. Use tools if needed
        3. Delegate if specialized
        4. Orchestrate if complex
        """

        text = user_input.lower()
        action = intent.get("action", "chat")

        # ==============================
        # 1️⃣ DIRECT ANSWERING (NOT JUST LISTENING)
        # ==============================
        if action == "chat":
            # If it's a clear question → answer directly
            if any(q in text for q in ["what", "why", "how", "when", "who"]):
                return {
                    "action": "respond",
                    "mode": "direct",
                    "response": intent.get("response", "Let me think...")
                }

        # ==============================
        # 2️⃣ TOOL USAGE (SELF EXECUTION)
        # ==============================
        if action in ["learn", "recall", "fix_code"]:
            return {
                "action": "use_tool",
                "tool": action
            }

        # ==============================
        # 3️⃣ SMART DELEGATION
        # ==============================
        if "build" in text or action == "build_app":
            return {
                "action": "delegate",
                "target": "app_builder"
            }

        if "analyze" in text:
            return {
                "action": "delegate",
                "target": "analysis_agent"
            }

        if "research" in text:
            return {
                "action": "delegate",
                "target": "research_agent"
            }

        if "code" in text or "fix" in text:
            return {
                "action": "delegate",
                "target": "code_agent"
            }

        # ==============================
        # 4️⃣ COMPLEX TASK → ORCHESTRATE
        # ==============================
        if len(text.split()) > 20:
            return {
                "action": "orchestrate",
                "reason": "complex_user_request"
            }

        # ==============================
        # DEFAULT → RESPOND
        # ==============================
        return {
            "action": "respond",
            "mode": "fallback",
            "response": intent.get("response", "Tell me more.")
        }

# =================================================
    # RULE ENGINE
    # =================================================
    def rule_engine(self, context: Dict[str, Any]) -> Dict[str, Any]:

        errors = " ".join(context.get("errors", [])).lower()

        if "syntaxerror" in errors:
            return {"action": "fix_code", "reason": "syntax"}

        if "modulenotfounderror" in errors:
            return {"action": "fix_code", "reason": "import"}

        if context.get("passed") is False:
            return {"action": "fix_code", "reason": "runtime"}

        return {"action": "chat"}

    # =================================================
    # LLM FALLBACK
    # =================================================
    def call_llm(self, prompt: str):

        if self.openai:
            try:
                res = self.openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                )
                return res.choices[0].message.content
            except:
                pass

        try:
            r = requests.post(self.ollama_url, json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False
            })
            return r.json().get("response", "")
        except:
            pass

        return ""

    # =================================================
    # 🧠 PLANNER (NOW ROLE-AWARE)
    # =================================================
    def planner(self, user_input: str, context: Dict[str, Any]):

        # 1️⃣ RULE ENGINE
        rule = self.rule_engine(context)
        if rule["action"] != "chat":
            return self.decide_role_action(rule)

        # 2️⃣ MEMORY SIGNALS
        if "what do i like" in user_input.lower():
            return {"action": "recall"}

        if user_input.lower().startswith("i "):
            return {"action": "learn"}

        # 3️⃣ INTENT DETECTION (NEW)
        if "build" in user_input.lower():
            return self.decide_role_action({"action": "build_app"}, user_input)

        if "analyze" in user_input.lower():
            return self.decide_role_action({"action": "analyze"}, user_input)

        if "research" in user_input.lower():
            return self.decide_role_action({"action": "research"}, user_input)

        # 4️⃣ LLM FALLBACK
        response = self.call_llm(f"Respond to: {user_input}")

        return self.decide_role_action({
            "action": "chat",
            "response": response or "Tell me more."
        }, user_input)

    # =================================================
    # TOOLS
    # =================================================
    def tool_fix_code(self, user_input: str, data: Dict[str, Any]):
        files = data.get("files", {})
        fixed = {}

        for name, code in files.items():
            code = re.sub(r'(\"[^\"]*$)', r'\1"', code)
            code = self._fix_indentation(code)

            if name == "main.py" and "if __name__" not in code:
                code += "\n\nif __name__ == '__main__':\n    print('App started')\n"

            fixed[name] = code

        return fixed

    def _fix_indentation(self, code: str):
        lines = code.split("\n")
        return "\n".join([("    " + l.strip()) if l.startswith(" ") else l for l in lines])

    def tool_learn(self, user_input: str, data: Any):
        norm = self._normalize(user_input)
        self.memory[norm] += 1
        self.last_seen[norm] = time.time()
        return "Learning saved."

    def tool_recall(self, user_input: str, data: Any):
        if not self.memory:
            return "Still learning about you."

        top = sorted(self.memory.items(), key=lambda x: -x[1])[:3]
        return "You often mention: " + ", ".join([k for k, _ in top])

    def tool_chat(self, user_input: str, data: Any):
        return data.get("response", "Tell me more.")

    # =================================================
    # 🚀 EXECUTION (ROLE-AWARE OUTPUT)
    # =================================================
    def step(self, user_input: str, context: Dict[str, Any] = None):

        context = context or {}
        self.decay_memory()

        plan = self.planner(user_input, context)
        action = plan.get("action", "chat")

        # 🧠 If Lily should NOT execute → return decision (for Engine)
        if action in ["delegate", "orchestrate"]:
            return plan

        tool = self.tools.get(action, self.tool_chat)
        result = tool(user_input, context if action == "fix_code" else plan)

        return {
            "action": "respond",
            "message": result
        }


# =================================================
# CLI (RESTORED)
# =================================================
    def run(self):
        print(f"[Lily] Hybrid Brain Online — {self.user_name} 🚀")

        while True:
            user_input = input("You: ").strip()

            if user_input.lower() in ["exit", "quit"]:
                break

            result = self.step(user_input)
            print("Lily:", result)


# =================================================
# RUN
# =================================================
if __name__ == "__main__":
    Lily("Reno").run()
