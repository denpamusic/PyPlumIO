"""Contains tasks helper."""
from __future__ import annotations

import asyncio
from typing import Any, Coroutine, Dict, Set


class TaskManager:
    """Helper class for working with asyncio tasks and futures."""

    _tasks: Set[asyncio.Task]
    _events: Dict[str, asyncio.Event]

    def __init__(self):
        self._tasks = set()
        self._events = {}

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

    def create_event(self, name: str) -> asyncio.Event:
        """Create the event."""
        if name in self.events:
            return self.events[name]

        event = asyncio.Event()
        self._events[name] = event
        return event

    def set_event(self, name: str) -> None:
        """Set the event."""
        if name in self.events:
            event = self.events[name]
            if not event.is_set():
                event.set()

    @property
    def tasks(self) -> Set[asyncio.Task]:
        """Return set of task references."""
        return self._tasks

    @property
    def events(self) -> Dict[str, asyncio.Event]:
        """Return events."""
        return self._events
