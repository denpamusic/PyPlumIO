"""Contains a task manager class."""
from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any


class TaskManager:
    """Represents a task manager."""

    _tasks: set[asyncio.Task]

    def __init__(self):
        """Initialize a new task manager."""
        self._tasks = set()

    def create_task(self, coro: Coroutine[Any, Any, Any]) -> asyncio.Task:
        """Create asyncio task and store a reference for it."""
        task: asyncio.Task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    def cancel_tasks(self):
        """Cancel all tasks."""
        for task in self._tasks:
            task.cancel()

    async def wait_until_done(self, return_exceptions: bool = True) -> None:
        """Wait for all tasks to complete."""
        await asyncio.gather(*self._tasks, return_exceptions=return_exceptions)

    @property
    def tasks(self) -> set[asyncio.Task]:
        """A list of tasks."""
        return self._tasks
