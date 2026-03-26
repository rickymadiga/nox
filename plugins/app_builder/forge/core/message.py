from typing import Any, Optional


class Message:
    """
    Simple message container for Forge event bus.
    """
    def __init__(
        self,
        sender: Optional[str] = None,
        recipient: Optional[str] = None,
        message_type: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
    ) -> None:
        self.sender = sender
        self.recipient = recipient
        self.message_type = message_type
        self.payload = payload or {}

    def __repr__(self) -> str:
        return (
            f"Message(sender={self.sender!r}, "
            f"recipient={self.recipient!r}, "
            f"type={self.message_type!r}, "
            f"payload_keys={list(self.payload.keys())})"
        )