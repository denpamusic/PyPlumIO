"""Contains an event manager class."""
from __future__ import annotations

import asyncio

from pyplumio.helpers.task_manager import TaskManager
from pyplumio.helpers.typing import EventCallbackType, EventDataType


class EventManager(TaskManager):
    """Represents an event manager."""

    data: EventDataType
    _events: dict[str | int, asyncio.Event]
    _callbacks: dict[str | int, list[EventCallbackType]]

    def __init__(self):
        """Initialize new event manager."""
        super().__init__()
        self.data = {}
        self._events = {}
        self._callbacks = {}

    def __getattr__(self, name: str):
        """Return attributes from the underlying data dictionary."""
        try:
            return self.data[name]
        except KeyError as e:
            raise AttributeError from e

    async def wait_for(self, name: str | int, timeout: float | None = None) -> None:
        """Wait for the value to become available."""
        if name not in self.data:
            await asyncio.wait_for(self.create_event(name).wait(), timeout=timeout)

    async def get(self, name: str | int, timeout: float | None = None):
        """Get the value."""
        await self.wait_for(name, timeout=timeout)
        return self.data[name]

    def get_nowait(self, name: str | int, default=None):
        """Get the value without waiting."""
        try:
            return self.data[name]
        except KeyError:
            return default

    def subscribe(self, name: str | int, callback: EventCallbackType) -> None:
        """Subscribe a callback to the event."""
        if name not in self._callbacks:
            self._callbacks[name] = []

        self._callbacks[name].append(callback)

    def subscribe_once(self, name: str | int, callback: EventCallbackType) -> None:
        """Subscribe a callback to the single event."""

        async def _callback(value):
            """Unsubscribe callback from the event and calls it."""
            self.unsubscribe(name, _callback)
            return await callback(value)

        self.subscribe(name, _callback)

    def unsubscribe(self, name: str | int, callback: EventCallbackType) -> None:
        """Usubscribe a callback from the event."""
        if name in self._callbacks and callback in self._callbacks[name]:
            self._callbacks[name].remove(callback)

    async def dispatch(self, name: str | int, value) -> None:
        """Call registered callbacks and dispatch the event."""
        if name in self._callbacks:
            callbacks = self._callbacks[name].copy()
            for callback in callbacks:
                return_value = await callback(value)
                value = return_value if return_value is not None else value

        self.data[name] = value
        self.set_event(name)

    def dispatch_nowait(self, name: str | int, value) -> None:
        """Call a registered callbacks and dispatch the event
        without waiting.
        """
        self.create_task(self.dispatch(name, value))

    def load(self, data: EventDataType) -> None:
        """Load event data."""

        async def _dispatch_events(data: EventDataType) -> None:
            """Dispatch events for a loaded data."""
            for key, value in data.items():
                await self.dispatch(key, value)

        self.data = data
        self.create_task(_dispatch_events(data))

    def create_event(self, name: str | int) -> asyncio.Event:
        """Create an event."""
        if name in self.events:
            return self.events[name]

        event = asyncio.Event()
        self._events[name] = event
        return event

    def set_event(self, name: str | int) -> None:
        """Set an event."""
        if name in self.events:
            event = self.events[name]
            if not event.is_set():
                event.set()

    async def shutdown(self) -> None:
        """Cancel scheduled tasks."""
        self.cancel_tasks()
        await self.wait_until_done()

    @property
    def events(self) -> dict[str | int, asyncio.Event]:
        """List of events."""
        return self._events
