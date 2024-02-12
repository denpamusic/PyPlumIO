"""Contains an event manager class."""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from pyplumio.helpers.task_manager import TaskManager


class EventManager(TaskManager):
    """Represents an event manager."""

    data: dict[str, Any]
    _events: dict[str, asyncio.Event]
    _callbacks: dict[str, list[Callable[[Any], Awaitable[Any]]]]

    def __init__(self) -> None:
        """Initialize a new event manager."""
        super().__init__()
        self.data = {}
        self._events = {}
        self._callbacks = {}

    def __getattr__(self, name: str) -> Any:
        """Return attributes from the underlying data dictionary."""
        try:
            return self.data[name]
        except KeyError as e:
            raise AttributeError from e

    async def wait_for(self, name: str, timeout: float | None = None) -> None:
        """Wait for the value to become available.

        :param name: Event name or ID
        :type name: str
        :param timeout: Wait this amount of seconds for a data to
            become available, defaults to `None`
        :type timeout: float, optional
        :raise asyncio.TimeoutError: when waiting past specified timeout
        """
        if name not in self.data:
            await asyncio.wait_for(self.create_event(name).wait(), timeout=timeout)

    async def get(self, name: str, timeout: float | None = None) -> Any:
        """Get the value by name.

        :param name: Event name or ID
        :type name: str
        :param timeout: Wait this amount of seconds for a data to
            become available, defaults to `None`
        :type timeout: float, optional
        :return: An event data
        :raise asyncio.TimeoutError: when waiting past specified timeout
        """
        await self.wait_for(name, timeout=timeout)
        return self.data[name]

    def get_nowait(self, name: str, default: Any = None) -> Any:
        """Get the value by name without waiting.

        If value is not available, default value will be
        returned instead.

        :param name: Event name or ID
        :type name: str
        :param default: default value to return if data is unavailable,
            defaults to `None`
        :type default: Any, optional
        :return: An event data
        """
        try:
            return self.data[name]
        except KeyError:
            return default

    def subscribe(self, name: str, callback: Callable[[Any], Awaitable[Any]]) -> None:
        """Subscribe a callback to the event.

        :param name: Event name or ID
        :type name: str
        :param callback: A coroutine callback function, that will be
            awaited on the with the event data as an argument.
        :type callback: Callable[[Any], Awaitable[Any]]
        """
        if name not in self._callbacks:
            self._callbacks[name] = []

        self._callbacks[name].append(callback)

    def subscribe_once(
        self, name: str, callback: Callable[[Any], Awaitable[Any]]
    ) -> None:
        """Subscribe a callback to the event once.

        Callback will be unsubscribed after single event.

        :param name: Event name or ID
        :type name: str
        :param callback: A coroutine callback function, that will be
            awaited on the with the event data as an argument.
        :type callback: Callable[[Any], Awaitable[Any]]
        """

        async def _callback(value: Any) -> Any:
            """Unsubscribe callback from the event and calls it."""
            self.unsubscribe(name, _callback)
            return await callback(value)

        self.subscribe(name, _callback)

    def unsubscribe(self, name: str, callback: Callable[[Any], Awaitable[Any]]) -> None:
        """Usubscribe a callback from the event.

        :param name: Event name or ID
        :type name: str
        :param callback: A coroutine callback function, previously
            subscribed to an event using ``subscribe()`` or
            ``subscribe_once()`` methods.
        :type callback: Callable[[Any], Awaitable[Any]]
        """
        if name in self._callbacks and callback in self._callbacks[name]:
            self._callbacks[name].remove(callback)

    async def dispatch(self, name: str, value: Any) -> None:
        """Call registered callbacks and dispatch the event."""
        if name in self._callbacks:
            callbacks = self._callbacks[name].copy()
            for callback in callbacks:
                return_value = await callback(value)
                value = return_value if return_value is not None else value

        self.data[name] = value
        self.set_event(name)

    def dispatch_nowait(self, name: str, value: Any) -> None:
        """Call a registered callbacks and dispatch the event without waiting."""
        self.create_task(self.dispatch(name, value))

    def load(self, data: dict[str, Any]) -> None:
        """Load an event data."""

        async def _dispatch_events(data: dict[str, Any]) -> None:
            """Dispatch events for a loaded data."""
            for key, value in data.items():
                await self.dispatch(key, value)

        self.data = data
        self.create_task(_dispatch_events(data))

    def create_event(self, name: str) -> asyncio.Event:
        """Create an event."""
        if name in self.events:
            return self.events[name]

        event = asyncio.Event()
        self._events[name] = event
        return event

    def set_event(self, name: str) -> None:
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
    def events(self) -> dict[str, asyncio.Event]:
        """Return the events."""
        return self._events
