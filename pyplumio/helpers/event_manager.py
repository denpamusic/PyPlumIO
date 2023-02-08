"""Contains event helper."""
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
        """Initialize the event manager object."""
        super().__init__()
        self.data = {}
        self._events = {}
        self._callbacks = {}

    def __getattr__(self, name: str):
        """Return attributes from the underlying data."""
        try:
            return self.data[name]
        except KeyError as e:
            raise AttributeError from e

    async def wait_for(self, name: str | int, timeout: float | None = None) -> None:
        """Waits for a data."""
        if name not in self.data:
            await asyncio.wait_for(self.create_event(name).wait(), timeout=timeout)

    async def get(self, name: str | int, timeout: float | None = None):
        """Return a value. When used with parameter, only it's
        value will be returned. To get the parameter object,
        get() method must be used instead."""
        await self.wait_for(name, timeout)
        return self.data[name]

    def get_nowait(self, name: str | int, default=None):
        """Get a value without waiting."""
        try:
            return self.data[name]
        except KeyError:
            return default

    def subscribe(self, name: str | int, callback: EventCallbackType) -> None:
        """Subscribe a callback to the value change event."""
        if name not in self._callbacks:
            self._callbacks[name] = []

        self._callbacks[name].append(callback)

    def subscribe_once(self, name: str | int, callback: EventCallbackType) -> None:
        """Subscribe a callback to the single value change event."""

        async def _callback(value):
            """Unsubscribe the callback and call it."""
            self.unsubscribe(name, _callback)
            return await callback(value)

        self.subscribe(name, _callback)

    def unsubscribe(self, name: str | int, callback: EventCallbackType) -> None:
        """Usubscribe a callback from the value change event."""
        if name in self._callbacks and callback in self._callbacks[name]:
            self._callbacks[name].remove(callback)

    async def async_dispatch(self, name: str | int, value) -> None:
        """Asynchronously call registered callbacks on value change."""
        if name in self._callbacks:
            callbacks = self._callbacks[name].copy()
            for callback in callbacks:
                return_value = await callback(value)
                value = return_value if return_value is not None else value

        self.data[name] = value
        self.set_event(name)

    def dispatch(self, *args, **kwargs) -> None:
        """Call registered callbacks on value change."""
        self.create_task(self.async_dispatch(*args, **kwargs))

    def load(self, data: EventDataType) -> None:
        """Load event data."""

        async def _dispatch_events(data: EventDataType) -> None:
            for key, value in data.items():
                await self.async_dispatch(key, value)

        self.data = data
        self.create_task(_dispatch_events(data))

    def create_event(self, name: str | int) -> asyncio.Event:
        """Create the event."""
        if name in self.events:
            return self.events[name]

        event = asyncio.Event()
        self._events[name] = event
        return event

    def set_event(self, name: str | int) -> None:
        """set the event."""
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
        """Return events."""
        return self._events
