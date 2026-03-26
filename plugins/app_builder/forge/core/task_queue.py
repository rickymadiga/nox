import asyncio
from typing import Any, Optional


class TaskQueue:

    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()

    async def add_task(self, task: Any) -> None:
        """Add a new task to the queue."""
        await self.queue.put(task)

    async def get_task(self, timeout: Optional[float] = None) -> Any:
        """Retrieve the next task."""
        if timeout:
            return await asyncio.wait_for(self.queue.get(), timeout)
        return await self.queue.get()

    def task_done(self) -> None:
        """Mark a task as completed."""
        self.queue.task_done()

    def size(self) -> int:
        """Return number of pending tasks."""
        return self.queue.qsize()

    async def wait_until_empty(self) -> None:
        """Block until all tasks are processed."""
        await self.queue.join()