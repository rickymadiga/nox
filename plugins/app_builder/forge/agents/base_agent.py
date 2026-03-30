class BaseAgent:
    """
    Base class for all Forge agents (DICT EVENT VERSION)
    """

    def __init__(self, name=None, bus=None, context=None):
        self.name = name
        self.bus = bus
        self.context = context or {}

    # ─────────────────────────────
    async def receive(self, message: dict) -> None:
        """
        Entry point for all events
        """

        if not isinstance(message, dict):
            return

        event_type = message.get("type")
        sender = message.get("sender", "unknown")

        print(f"[{self.name}] received {event_type} from {sender}")

        try:
            await self.handle(message)

        except Exception as e:
            print(
                f"[Agent ERROR] {self.name} failed handling "
                f"{event_type}: {type(e).__name__}: {e}"
            )

    # ─────────────────────────────
    async def handle(self, message: dict) -> None:
        raise NotImplementedError

    # ─────────────────────────────
    async def publish(self, event: dict) -> None:
        if not self.bus:
            raise RuntimeError("Agent has no event bus")

        await self.bus.publish(event)

    # ─────────────────────────────
    def register(self) -> None:
        pass