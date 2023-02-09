"""Contains tasks helper."""
from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any


class TaskManager:
    """Represents task manager."""

    _tasks: set[asyncio.Task]

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

    async def wait_until_done(self, return_exceptions: bool = True) -> None:
        """Wait for all task to complete."""
        await asyncio.gather(*self._tasks, return_exceptions=return_exceptions)

    @property
    def tasks(self) -> set[asyncio.Task]:
        """Return set of task references."""
        return self._tasks
