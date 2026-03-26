import asyncio


class EventBus:

    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_name: str, callback):

        if event_name not in self.subscribers:
            self.subscribers[event_name] = []

        self.subscribers[event_name].append(callback)

        print(f"[EventBus] {callback.__name__} subscribed to {event_name}")

    def unsubscribe(self, event_name: str, callback):

        if event_name in self.subscribers:
            if callback in self.subscribers[event_name]:
                self.subscribers[event_name].remove(callback)

    async def publish(self, message):

        event_name = getattr(message, "message_type", None)

        if not event_name:
            raise ValueError("Message missing message_type")

        print(f"[EventBus] Publishing event: {event_name}")

        if event_name not in self.subscribers:
            print(f"[EventBus] No subscribers for {event_name}")
            return

        tasks = []

        for callback in self.subscribers[event_name]:

            try:

                if asyncio.iscoroutinefunction(callback):

                    tasks.append(callback(message))

                else:

                    tasks.append(asyncio.to_thread(callback, message))

            except Exception as e:

                print(f"[EventBus ERROR] {callback} failed: {e}")

        if tasks:

            await asyncio.gather(*tasks, return_exceptions=True)