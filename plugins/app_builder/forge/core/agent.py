from typing import Any, Optional


class Agent:
    """
    Base class for all Forge agents.

    Responsibilities:
    - Holds agent identity
    - Connects to the event bus
    - Routes incoming messages to `handle()`

    Subclasses must implement `handle()`.
    """

    def __init__(self, name=None, bus=None, context=None):
        self.name = name
        self.bus = bus
        self.context = context or {}

    async def receive(self, message: Any) -> None:
        """
        Entry point for messages coming from the bus.

        Flow:
        1. Ensure message has a recipient
        2. Check if this agent is the intended target
        3. Forward message to `handle()`
        """

        # Ignore messages without a recipient field
        if not hasattr(message, "recipient"):
            return

        # Ignore messages not intended for this agent
        if message.recipient != self.name:
            return

        print(f"[{self.__class__.__name__}] received {message.message_type}")

        await self.handle(message)

    async def handle(self, message: Any) -> None:
        """
        Process a message addressed to this agent.

        Must be implemented by subclasses.
        """
        raise NotImplementedError(
            f"Agent {self.__class__.__name__} ({self.name}) must implement `.handle()`"
        )

    def register(self) -> None:
        """
        Hook for bus subscription.

        Subclasses override this method to subscribe
        to specific message types.

        Called by:
        - `bus.register(self)`
        - or manually inside `arena.py`
        """
        # Base agent does not subscribe to anything
        pass