import asyncio
from typing import Any, Callable, Dict, List


class EventBus:

    def __init__(self) -> None:
        self.subscribers: Dict[str, List[Callable]] = {}
        print("[EventBus] Initialized")

    # -----------------------------
    # Subscribe
    # -----------------------------
    def subscribe(self, event_type: str, handler: Callable):

        self.subscribers.setdefault(event_type, []).append(handler)

        agent = getattr(handler.__self__, "name", "unknown")

        print(f"[EventBus] {agent} subscribed → {event_type}")

    # -----------------------------
    # Publish
    # -----------------------------
    async def publish(self, message: Any):

        if not hasattr(message, "message_type"):
            print("[EventBus] Dropped message (no message_type)")
            return

        msg_type = message.message_type
        sender = getattr(message, "sender", "unknown")
        recipient = getattr(message, "recipient", None)

        handlers = self.subscribers.get(msg_type, [])

        print(
            f"[EventBus] {msg_type} | from={sender} | "
            f"handlers={len(handlers)} | to={recipient}"
        )

        if not handlers:
            return

        tasks = []

        for handler in handlers:

            agent = getattr(handler.__self__, "name", None)

            # ✅ STRICT ROUTING (your architecture)
            if recipient and recipient != agent:
                continue

            tasks.append(self._safe_execute(handler, message, agent))

        if tasks:
            await asyncio.gather(*tasks["user_id"])

    # -----------------------------
    # Safe execution
    # -----------------------------
    async def _safe_execute(self, handler, message, agent):

        try:
            await handler(message)

        except Exception as e:

            print(
                f"[EventBus ERROR] agent={agent} | "
                f"{type(e).__name__}: {e}"
            )

    # -----------------------------
    # Debug
    # -----------------------------
    def stats(self):

        print("\n[EventBus] Subscriber Map")

        for event, handlers in self.subscribers.items():
            agents = [
                getattr(h.__self__, "name", "unknown")
                for h in handlers
            ]
            print(f"{event} → {agents}")

        print()