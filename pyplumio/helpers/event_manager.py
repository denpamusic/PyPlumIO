"""Contains an event manager class."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine, Generator
import inspect
from types import MappingProxyType
from typing import Any, Generic, TypeAlias, TypeVar, overload

from pyplumio.helpers.task_manager import TaskManager

Callback: TypeAlias = Callable[[Any], Coroutine[Any, Any, Any]]

_CallableT: TypeAlias = Callable[..., Any]
_CallbackT = TypeVar("_CallbackT", bound=Callback)


@overload
def event_listener(name: _CallableT, filter: None = None) -> Callback: ...


@overload
def event_listener(
    name: str | None = None, filter: _CallableT | None = None
) -> _CallableT: ...


def event_listener(name: Any = None, filter: _CallableT | None = None) -> Any:
    """Mark a function as an event listener.

    This decorator attaches metadata to the function, identifying it
    as a subscriber for the specified event.
    """

    def decorator(func: _CallbackT) -> _CallbackT:
        # Attach metadata to the function to mark it as a listener.
        event = (
            name
            if isinstance(name, str)
            else func.__qualname__.split("on_event_", 1)[1]
        )
        setattr(func, "_on_event", event)
        setattr(func, "_on_event_filter", filter)
        return func

    if callable(name):
        return decorator(name)
    else:
        return decorator


T = TypeVar("T")


class EventManager(TaskManager, Generic[T]):
    """Represents an event manager."""

    __slots__ = ("_data", "_events", "_callbacks")

    _data: dict[str, T]
    _events: dict[str, asyncio.Event]
    _callbacks: dict[str, list[Callback]]

    def __init__(self) -> None:
        """Initialize a new event manager."""
        super().__init__()
        self._data = {}
        self._events = {}
        self._callbacks = {}
        self._register_event_listeners()

    def __getattr__(self, name: str) -> T:
        """Return attributes from the underlying data dictionary."""
        try:
            return self.data[name]
        except KeyError as e:
            raise AttributeError from e

    def _register_event_listeners(self) -> None:
        """Register the event listeners."""
        for event, callback in self.event_listeners():
            filter_func = getattr(callback, "_on_event_filter", None)
            self.subscribe(event, filter_func(callback) if filter_func else callback)

    def event_listeners(self) -> Generator[tuple[str, Callback]]:
        """Get the event listeners."""
        for _, callback in inspect.getmembers(self, predicate=inspect.ismethod):
            if event := getattr(callback, "_on_event", None):
                yield (event, callback)

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

    async def get(self, name: str, timeout: float | None = None) -> T:
        """Get the value by name.

        :param name: Event name or ID
        :type name: str
        :param timeout: Wait this amount of seconds for a data to
            become available, defaults to `None`
        :type timeout: float, optional
        :return: An event data
        :rtype: T
        :raise asyncio.TimeoutError: when waiting past specified timeout
        """
        await self.wait_for(name, timeout=timeout)
        return self.data[name]

    @overload
    def get_nowait(self, name: str, default: None = ...) -> T | None: ...

    @overload
    def get_nowait(self, name: str, default: T) -> T: ...

    def get_nowait(self, name: str, default: Any = None) -> Any:
        """Get the value by name without waiting.

        If value is not available, default value will be
        returned instead.

        :param name: Event name or ID
        :type name: str
        :param default: default value to return if data is unavailable,
            defaults to `None`
        :type default: T, optional
        :return: An event data
        :rtype: T, optional
        """
        try:
            return self.data[name]
        except KeyError:
            return default

    def subscribe(self, name: str, callback: _CallbackT) -> _CallbackT:
        """Subscribe a callback to the event.

        :param name: Event name or ID
        :type name: str
        :param callback: A coroutine callback function, that will be
            awaited on the with the event data as an argument.
        :type callback: Callback
        :return: A reference to the callback, that can be used
            with `EventManager.unsubscribe()`.
        :rtype: Callback
        """
        callbacks = self._callbacks.setdefault(name, [])
        callbacks.append(callback)
        return callback

    def subscribe_once(self, name: str, callback: Callback) -> Callback:
        """Subscribe a callback to the event once.

        Callback will be unsubscribed after single event.

        :param name: Event name or ID
        :type name: str
        :param callback: A coroutine callback function, that will be
            awaited on the with the event data as an argument.
        :type callback: Callback
        :return: A reference to the callback, that can be used
            with `EventManager.unsubscribe()`.
        :rtype: Callback
        """

        async def _call_once(value: Any) -> Any:
            """Unsubscribe callback from the event and calls it."""
            self.unsubscribe(name, _call_once)
            return await callback(value)

        return self.subscribe(name, _call_once)

    def unsubscribe(self, name: str, callback: Callback) -> bool:
        """Usubscribe a callback from the event.

        :param name: Event name or ID
        :type name: str
        :param callback: A coroutine callback function, previously
            subscribed to an event using ``subscribe()`` or
            ``subscribe_once()`` methods.
        :type callback: Callback
        :return: `True` if callback is found, `False` otherwise.
        :rtype: bool
        """
        if name in self._callbacks and callback in self._callbacks[name]:
            self._callbacks[name].remove(callback)
            return True

        return False

    async def dispatch(self, name: str, value: T) -> None:
        """Call registered callbacks and dispatch the event."""
        if callbacks := self._callbacks.get(name, None):
            for callback in list(callbacks):
                if (result := await callback(value)) is not None:
                    value = result

        self._data[name] = value
        self.set_event(name)

    def dispatch_nowait(self, name: str, value: T) -> None:
        """Call a registered callbacks and dispatch the event without waiting."""
        self.create_task(self.dispatch(name, value))

    async def load(self, data: dict[str, T]) -> None:
        """Load event data."""
        await asyncio.gather(
            *(self.dispatch(name, value) for name, value in data.items())
        )

    def load_nowait(self, data: dict[str, T]) -> None:
        """Load event data without waiting."""
        self.create_task(self.load(data))

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
            self.events[name].set()

    @property
    def events(self) -> dict[str, asyncio.Event]:
        """Return the events."""
        return self._events

    @property
    def data(self) -> MappingProxyType[str, T]:
        """Return the event data."""
        return MappingProxyType(self._data)


__all__ = ["Callback", "EventManager", "event_listener"]
