"""Contains a task manager class."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any


class TaskManager:
    """Represents a task manager."""

    _tasks: set[asyncio.Task]

    def __init__(self) -> None:
        """Initialize a new task manager."""
        self._tasks = set()

    def create_task(
        self, coro: Coroutine[Any, Any, Any], name: str | None = None
    ) -> asyncio.Task:
        """Create asyncio task and store a reference for it."""
        task = asyncio.create_task(coro, name=name)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    def cancel_tasks(self) -> bool:
        """Cancel all tasks."""
        return all(task.cancel() for task in self._tasks)

    async def wait_until_done(self, return_exceptions: bool = True) -> None:
        """Wait for all tasks to complete."""
        await asyncio.gather(*self._tasks, return_exceptions=return_exceptions)

    @property
    def tasks(self) -> set[asyncio.Task]:
        """Return the tasks."""
        return self._tasks
