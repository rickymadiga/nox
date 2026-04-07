from nox.core.agent import Agent
from nox.core.message import Message


class CodeAgent(Agent):
    """
    Observes the Forge pipeline and streams live progress/logs 
    to the frontend via runtime.logs and the /stream endpoint.
    """

    def __init__(self, runtime):
        super().__init__(runtime)

        self.runtime = runtime
        self.bus = runtime.bus
        self.name = "code_agent"

        # 🔥 Subscribe to important pipeline events
        events = [
            "TASK_REQUEST",
            "PLAN_CREATED",
            "CODE_GENERATED",
            "TEST_RESULTS",
            "REVIEW_COMPLETED",
            "CODE_APPROVED",
            "forge_complete",
        ]

        for event in events:
            self.bus.subscribe(event, self.on_event)

        print(f"[{self.name}] Watching Forge pipeline for live updates...")

    # ─────────────────────────────────────────────
    async def on_event(self, message: Message):
        """Process events and push logs to runtime (shared with frontend)."""
        try:
            event_type = getattr(message, "message_type", None)
            if not event_type:
                return

            payload = getattr(message, "payload", {}) or {}

            # Build rich log line
            log_line = f"🔹 {event_type}"

            if task := payload.get("task"):
                log_line += f" → {task}"
            if status := payload.get("status"):
                log_line += f" [{status}]"
            if msg := payload.get("message"):
                log_line += f" | {msg}"

            # Ensure runtime.logs list exists
            if not hasattr(self.runtime, "logs") or self.runtime.logs is None:
                self.runtime.logs = []

            self.runtime.logs.append(log_line)

            # Keep only last 100 logs to avoid memory growth
            if len(self.runtime.logs) > 100:
                self.runtime.logs = self.runtime.logs[-100:]

            print(f"[{self.name}] {log_line}")

        except Exception as e:
            print(f"[{self.name} ERROR] {e}")

    # ─────────────────────────────────────────────
    def run(self, task: dict):
        """Fallback handler when CodeAgent is called directly via engine."""
        prompt = task.get("prompt", "").strip() or "(no prompt)"

        return {
            "message": f"CodeAgent received: {prompt[:120]}{'...' if len(prompt) > 120 else ''}",
            "status": "received",
            "agent": "code_agent"
        }


# ─────────────────────────────────────────────
# PLUGIN ENTRY POINT (This is what the loader looks for)
# ─────────────────────────────────────────────
def register(runtime):
    """This function is called by plugin_loader."""
    agent = CodeAgent(runtime)
    runtime.register_agent("code_agent", agent)
    print("[PLUGIN] Code Agent loaded ✅")