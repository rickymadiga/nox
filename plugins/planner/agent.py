class PlannerAgent:
    """
    Planner is now a SUPPORT agent.
    It suggests execution strategies but DOES NOT take control.
    """

    def __init__(self, runtime):
        self.runtime = runtime

        # Confidence threshold
        self.threshold = 0.35

        # Agent priority (used for ranking only)
        self.agent_priority = {
            "app_builder": 12,
            "analytics": 10,
            "calculator": 9,
            "web_agent": 8,
            "weather": 7,
            "chat": 6,
            "lily": 100  # Lily always highest (just for safety)
        }

        # Intent keywords
        self.intent_map = {
            "build_app": ["build", "create", "generate", "make", "develop"],
            "math": ["calculate", "compute", "sum", "average", "+", "-", "*", "/"],
            "weather": ["weather", "forecast", "temperature", "rain"],
            "web": ["search", "find", "look up", "google"]
        }

    async def run(self, task):
        """
        Returns a PLAN, not a final decision.
        Lily decides whether to follow it or not.
        """

        prompt = str(task.get("prompt", "")).strip().lower()

        print(f"[Planner] Planning for: {prompt}")

        # ─────────────────────────────
        # 1. Intent detection
        # ─────────────────────────────
        intent = self.detect_intent(prompt)

        print(f"[Planner] Detected intent: {intent}")

        # ─────────────────────────────
        # 2. Intent-based suggestions
        # ─────────────────────────────
        if intent == "build_app":
            return self._plan(["app_builder"], strategy="intent_route", confidence=1.0)

        if intent == "math":
            return self._plan(["calculator", "analytics"], strategy="intent_route", confidence=1.0)

        if intent == "weather":
            return self._plan(["weather"], strategy="intent_route", confidence=1.0)

        if intent == "web":
            return self._plan(["web_agent"], strategy="intent_route", confidence=1.0)

        # ─────────────────────────────
        # 3. Capability fallback
        # ─────────────────────────────
        matches = self.runtime.capabilities.match_agents(prompt)

        if not matches:
            print("[Planner] No matches → fallback to chat")

            return self._plan(
                ["chat"],
                strategy="fallback",
                confidence=0.3
            )

        matches = sorted(
            matches,
            key=lambda m: (
                m.get("score", 0),
                self.agent_priority.get(m.get("agent"), 0)
            ),
            reverse=True
        )

        best = matches[0]

        print(f"[Planner] Best match → {best['agent']} score={best['score']}")

        if best["score"] < self.threshold:
            return self._plan(
                ["chat"],
                strategy="low_confidence",
                confidence=best["score"]
            )

        return self._plan(
            [best["agent"]],
            strategy="capability_match",
            confidence=best["score"]
        )

    # ─────────────────────────────
    # Helper: build plan
    # ─────────────────────────────
    def _plan(self, agents, strategy, confidence):
        return {
            "type": "plan",  # 🔥 important (Lily will detect this)
            "strategy": strategy,
            "agents": agents,
            "confidence": confidence
        }

    # ─────────────────────────────
    # Intent detection
    # ─────────────────────────────
    def detect_intent(self, prompt):

        for intent, keywords in self.intent_map.items():
            if any(word in prompt for word in keywords):
                return intent

        return "unknown"