from typing import Any, Optional
from ..core.message import Message


class BaseAgent:
    """
    Base class for all Forge agents.

    Responsibilities
    ----------------
    • Hold agent identity
    • Receive messages from EventBus
    • Route messages to handle()
    • Provide helper utilities for publishing events
    """

    def __init__(self, name=None, bus=None, context=None):

        self.name = name
        self.bus = bus
        self.context = context or {}

    # ---------------------------------
    # MESSAGE ENTRYPOINT
    # ---------------------------------

    async def receive(self, message: Any) -> None:
        """
        Entry point for all messages delivered by EventBus.
        """

        if not hasattr(message, "message_type"):
            return

        recipient = getattr(message, "recipient", None)

        # Skip if message intended for someone else
        if recipient and recipient != self.name:
            return

        print(
            f"[{self.name}] received {message.message_type} "
            f"from {getattr(message, 'sender', 'unknown')}"
        )

        try:
            await self.handle(message)

        except Exception as e:

            print(
                f"[Agent ERROR] {self.name} failed handling "
                f"{message.message_type}: {type(e).__name__}: {e}"
            )

    # ---------------------------------
    # MESSAGE HANDLER (override)
    # ---------------------------------

    async def handle(self, message: Any) -> None:
        """
        Subclasses must implement this.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement handle()"
        )

    # ---------------------------------
    # EVENT PUBLISH HELPER
    # ---------------------------------

    async def publish(self, message) -> None:

        if not self.bus:
            raise RuntimeError("Agent has no event bus")

        await self.bus.publish(message)

    # ---------------------------------
    # SUBSCRIPTION HOOK
    # ---------------------------------

    def register(self) -> None:
        """
        Override in subclasses to subscribe to events.
        """
        pass