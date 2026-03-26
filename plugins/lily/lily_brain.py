# lily_brain.py — NOX GOD BRAIN (v7.1 ENHANCED UNDERSTANDING & BUILD DETECTION)

import os
import re
import time
import requests
from typing import Dict, Any, List


class Lily:
    def __init__(self, user_name: str = "NOX", llm=None):
        self.user_name = user_name
        self.memory: Dict[str, int] = {}
        self.last_seen: Dict[str, float] = {}

        # Structured Memory
        self.structured_memory: Dict[str, Any] = {
            "likes": [],
            "goals": [],
            "project": None
        }
        self.conversation_history: List[Dict[str, str]] = []

        self.agent_stats: Dict[str, Dict] = {}
        self.llm = llm
        self.openai = None
        self.ollama = False
        self.ollama_url = "http://localhost:11434/api/generate"
        self.step = 0

        self._init_models()

    # =========================================================
    # INIT
    # =========================================================
    def _init_models(self):
        if os.getenv("OPENAI_API_KEY"):
            try:
                from openai import OpenAI
                self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                print("[Lily] OpenAI ✓")
            except Exception as e:
                print("[Lily] OpenAI init failed:", e)

        try:
            requests.get("http://localhost:11434", timeout=1)
            self.ollama = True
            print("[Lily] Ollama ✓")
        except:
            pass

    # =========================================================
    # HELPERS
    # =========================================================
    def _safe_text(self, value):
        if isinstance(value, dict):
            return value.get("input") or value.get("prompt") or ""
        return str(value)

    def _normalize(self, text: str) -> str:
        return re.sub(r"[^a-z0-9\s]", "", text.lower()).strip()

    # =========================================================
    # 🔥 MEMORY EXTRACTION
    # =========================================================
    def extract_memory(self, text: str):
        """Extract likes, goals, and project from user input"""
        t = text.lower()

        if "i like" in t:
            value = t.split("i like")[-1].strip()
            if value and value not in self.structured_memory.get("likes", []):
                self.structured_memory.setdefault("likes", []).append(value)
                print(f"[Lily Memory] Learned like: {value}")

        if "i want to" in t or "i plan to" in t:
            goal = t.replace("i want to", "").replace("i plan to", "").strip()
            if goal and goal not in self.structured_memory.get("goals", []):
                self.structured_memory.setdefault("goals", []).append(goal)
                print(f"[Lily Memory] Learned goal: {goal}")

        if "i am building" in t or "i'm building" in t or "building a" in t:
            self.structured_memory["project"] = text
            print(f"[Lily Memory] Learned project: {text}")

    # =========================================================
    # CONVERSATION MEMORY
    # =========================================================
    def add_to_history(self, role: str, content: str):
        self.conversation_history.append({
            "role": role,
            "content": content
        })

        if len(self.conversation_history) > 10:
            self.conversation_history.pop(0)

    def build_context_prompt(self, user_input: str) -> str:
        history = ""
        for msg in self.conversation_history[-6:]:
            history += f"{msg['role']}: {msg['content']}\n"

        likes = self.structured_memory.get("likes", [])
        project = self.structured_memory.get("project")

        user_info = ""
        if likes:
            user_info += f"User likes: {', '.join(likes)}\n"
        if project:
            user_info += f"User is building: {project}\n"

        return f"""
You are Lily, a warm, intelligent, and helpful assistant.

User Profile:
{user_info}

Conversation so far:
{history}

User: {user_input}

Respond in a natural, friendly, and context-aware way. Reference what you know about the user when relevant.
"""

    # =========================================================
    # INTENT CLASSIFIER
    # =========================================================
    def classify_intent(self, text: str) -> str:
        t = text.lower()

        if any(x in t for x in ["hello", "hi", "hey", "yo"]):
            return "greeting"

        if "joke" in t or "funny" in t:
            return "fun"

        if "what am i building" in t or "what am i working on" in t:
            return "recall_project"

        if "i am building" in t or "i'm building" in t:
            return "store_project"

        if any(x in t for x in ["build", "create", "make"]):
            return "build"

        if any(x in t for x in ["fix", "error", "bug"]):
            return "fix"

        return "general"

    # =========================================================
    # DECISION ENGINE
    # =========================================================
    def decide(self, user_input: str, context: Dict[str, Any]):
        text = user_input.lower()

        # Extract memory from every input
        self.extract_memory(user_input)

        intent = self.classify_intent(user_input)

        # =========================
        # BUILD KEYWORDS DETECTION (Your new block)
        # =========================
        build_keywords = ["build", "create", "make", "generate", "develop"]

        if any(k in text for k in build_keywords):
            if len(text.split()) > 3:  # avoid triggering on short messages
                candidates = ["app_builder", "code_agent", "web_agent"]
                return {
                    "action": "delegate_multi",
                    "targets": self.select_top_agents(candidates)
                }

        # "What do I like?" recall
        if "what do i like" in text:
            likes = self.structured_memory.get("likes", [])
            if likes:
                return {
                    "action": "respond",
                    "message": "You like: " + ", ".join(likes)
                }
            return {
                "action": "respond",
                "message": "I don't know what you like yet. Tell me!"
            }

        # Store project
        if intent == "store_project":
            self.structured_memory["project"] = user_input
            return {
                "action": "respond",
                "message": "Got it! I'll remember you're building this."
            }

        # Recall project
        if intent == "recall_project":
            project = self.structured_memory.get("project")
            if project:
                return {
                    "action": "respond",
                    "message": f"You're currently building: {project}"
                }
            return {
                "action": "respond",
                "message": "You haven't told me what you're building yet."
            }

        # Greeting
        if intent == "greeting":
            return {
                "action": "respond",
                "message": "Hey 👋 What are you working on today?"
            }

        # Fun
        if intent == "fun":
            return {
                "action": "respond",
                "message": "Why do programmers hate nature? Too many bugs 😄"
            }

        # Delegation (fallback from intent classifier)
        if intent == "build":
            return {
                "action": "delegate_multi",
                "targets": ["app_builder", "code_agent"]
            }

        if intent == "fix":
            return {"action": "delegate", "target": "code_agent"}

        # Default: LLM with rich context
        prompt = self.build_context_prompt(user_input)
        response = self.call_llm(prompt)

        # Smart fallback using memory if LLM response is weak
        if not response or len(response.strip()) < 5:
            likes = self.structured_memory.get("likes", [])
            project = self.structured_memory.get("project")

            if project:
                return {
                    "action": "respond",
                    "message": f"You're building {project}. How can I help with that?"
                }
            elif likes:
                return {
                    "action": "respond",
                    "message": f"You've mentioned you like {likes[0]}. Want to build something related to it?"
                }

        return {
            "action": "respond",
            "message": response or "Tell me more about that. I'm here to help!"
        }

    # =========================================================
    # SELECT TOP AGENTS (required for delegate_multi)
    # =========================================================
    def select_top_agents(self, candidates: List[str], top_n: int = 3) -> List[str]:
        """Select top agents based on stats (fallback to all if no stats)"""
        if not candidates:
            return []

        ranked = []
        for agent in candidates:
            stats = self.agent_stats.get(agent, {"score": 1.0})
            ranked.append((agent, stats.get("score", 1.0)))

        ranked.sort(key=lambda x: x[1], reverse=True)
        return [agent for agent, _ in ranked[:top_n]]

    # =========================================================
    # LLM CALL
    # =========================================================
    def call_llm(self, prompt: str) -> str:
        if self.openai:
            try:
                res = self.openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                return res.choices[0].message.content
            except:
                pass

        if self.ollama:
            try:
                r = requests.post(self.ollama_url, json={
                    "model": "llama3",
                    "prompt": prompt,
                    "stream": False
                }, timeout=15)
                return r.json().get("response", "")
            except:
                pass

        return ""

    # =========================================================
    # SYNTHESIZE RESULTS
    # =========================================================
    def _synthesize(self, results: Dict[str, Any], plan: List[str]) -> str:
        if not results:
            return "No output."

        messages = []

        for agent, res in results.items():
            if isinstance(res, dict):
                if "message" in res:
                    messages.append(res["message"])
                    continue
                if "response" in res:
                    messages.append(res["response"])
                    continue
                if "output" in res:
                    messages.append(res["output"])
                    continue

                if agent == "app_builder":
                    forge = res.get("forge_result", {})
                    if forge.get("status") == "completed":
                        messages.append(f"✅ App built successfully\n📁 {forge.get('task', '')}")
                        continue

                messages.append(f"{agent}: {str(res)}")
            else:
                messages.append(f"{agent}: {str(res)}")

        return "\n\n".join(messages)

    # =========================================================
    # MAIN ENTRY
    # =========================================================
    def run(self, task: Dict[str, Any]):
        user_input = self._safe_text(task)
        context = task.get("context", {}) if isinstance(task, dict) else {}

        self.step += 1
        print(f"[LILY] Step {self.step} | Input: {user_input}")

        self.add_to_history("user", user_input)

        decision = self.decide(user_input, context)

        if decision.get("action") == "respond":
            self.add_to_history("assistant", decision.get("message", ""))

        return decision


# =================================================
# PLUGIN ENTRY
# =================================================
def register(runtime):
    lily = Lily()
    runtime.register_agent("lily", lily)
    print("[PLUGIN] Lily GOD Brain v7.1 registered 🚀")