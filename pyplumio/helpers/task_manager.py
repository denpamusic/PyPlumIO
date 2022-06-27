"""Contains tasks helper."""

import asyncio
from typing import Any, Coroutine, Iterable, Set


class TaskManager:
    """Helper class for working with asyncio tasks and storing
    references."""

    _tasks: Set[asyncio.Task]

    def __init__(self):
        self._tasks = set()

    def create_task(self, coro: Coroutine[Any, Any, Any]) -> asyncio.Task:
        """Create asyncio Task and store it's reference."""
        task: asyncio.Task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    def cancel_tasks(self):
        """Cancel all tasks."""
        for task in self._tasks:
            task.cancel()

    async def wait_for_tasks(self, return_exceptions: bool = True) -> None:
        """Wait for all task to complete."""
        await asyncio.gather(*self._tasks, return_exceptions=return_exceptions)

    @property
    def tasks(self) -> Iterable[asyncio.Task]:
        """Return set of task references."""
        return self._tasks
