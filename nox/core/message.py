class Message:
    def __init__(self, sender, recipient, message_type, payload=None):
        self.sender = sender
        self.recipient = recipient
        self.message_type = message_type
        self.payload = payload or {}