class MessageBus:

    def __init__(self):
        self.subscribers = {}
        self.messages = []

    def subscribe(self, event, agent):

        if event not in self.subscribers:
            self.subscribers[event] = []

        self.subscribers[event].append(agent)

    async def publish(self, event, data):

        self.messages.append({
            "event": event,
            "data": data
        })

        if event in self.subscribers:

            for agent in self.subscribers[event]:
                await agent.handle_event(event, data)