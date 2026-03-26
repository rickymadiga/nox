from .message import Message


class Scheduler:

    def __init__(self, bus):
        self.bus = bus

    async def dispatch_task(self, task):

        message = Message(
            type="TASK_REQUEST",
            payload={"task": task}
        )

        await self.bus.publish(message)