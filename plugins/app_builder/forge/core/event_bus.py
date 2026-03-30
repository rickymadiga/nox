import asyncio
from typing import Any, Callable, Dict, List


class EventBus:

    def __init__(self) -> None:
        self.subscribers: Dict[str, List[Callable]] = {}
        print("[EventBus] Initialized")

    # -----------------------------
    # Subscribe
    # -----------------------------
    def subscribe(self, event_type, handler):
     if event_type not in self.subscribers:
        self.subscribers[event_type] = []

        self.subscribers[event_type].append(handler)
        print(f"[EventBus] subscribed → {event_type}")

    # -----------------------------
    # Publish
    # -----------------------------
    
    async def publish(self, message):

    # 🔥 SUPPORT BOTH dict + old Message (safety)
     if isinstance(message, dict):
        message_type = message.get("type")
     else:
        message_type = getattr(message, "message_type", None)

     if not message_type:
        print("[EventBus] Dropped message (no message_type)")
        return

     handlers = self.subscribers.get(message_type, [])

     print(f"[EventBus] {message_type} | handlers={len(handlers)}")

     for handler in handlers:
        try:
            await handler(message)
        except Exception as e:
            print(f"[EventBus ERROR] {e}")

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