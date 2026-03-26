import numpy as np


class CapabilityIndex:
    def __init__(self):
        self.capabilities = []
        self.priorities = {}
        self.embeddings = []
        self.model = None  # optional embedding model

    # ─────────────────────────────
    # REGISTER
    # ─────────────────────────────
    def register(self, agent_name: str, intent: str, keywords: list):
        entry = {
            "agent": agent_name,
            "intent": intent,
            "keywords": keywords
        }

        self.capabilities.append(entry)

    def set_priority(self, agent_name: str, priority: int):
        self.priorities[agent_name] = priority

    # ─────────────────────────────
    # TOP-K MATCH (KEY FEATURE)
    # ─────────────────────────────
    def match(self, prompt: str, top_k: int = 3):
        prompt = prompt.lower()

        scored = []

        for cap in self.capabilities:
            agent = cap["agent"]
            score = 0

            for kw in cap["keywords"]:
                if kw in prompt:
                    score += 1

            if score > 0:
                scored.append({
                    "agent": agent,
                    "score": score,
                    "priority": self.priorities.get(agent, 0)
                })

        # sort by priority THEN score
        scored.sort(
            key=lambda x: (x["priority"], x["score"]),
            reverse=True
        )

        # return ONLY agent names
        return [s["agent"] for s in scored[:top_k]]

    # ─────────────────────────────
    # OPTIONAL: EMBEDDING MATCH
    # ─────────────────────────────
    def match_with_embeddings(self, prompt: str, top_k: int = 3):
        if not self.model or not self.embeddings:
            return self.match(prompt, top_k)

        try:
            query = self.model.encode(prompt)

            sims = []
            for emb in self.embeddings:
                sim = np.dot(query, emb) / (
                    np.linalg.norm(query) * np.linalg.norm(emb)
                )
                sims.append(sim)

            best_idx = int(np.argmax(sims))
            return [self.capabilities[best_idx]["agent"]]

        except Exception as e:
            print(f"[CapabilityIndex] embedding error: {e}")
            return self.match(prompt, top_k)