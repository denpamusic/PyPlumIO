"""Contains an event manager class."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine, Generator
from dataclasses import dataclass, field
import inspect
import logging
from types import MappingProxyType
from typing import Any, Generic, TypeAlias, TypeVar, overload

from pyplumio.helpers.task_manager import TaskManager

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class EventListener:
    """Represents an event listener."""

    callback: EventCallback
    priority: int = field(default=1, compare=False)


EventCallback: TypeAlias = Callable[[Any], Coroutine[Any, Any, Any]]
_Callable: TypeAlias = Callable[..., Any]

_EventCallbackT = TypeVar("_EventCallbackT", bound=EventCallback)


@overload
def event_listener(
    name: _Callable, filter: None = None, *, priority: int = 1
) -> EventCallback: ...


@overload
def event_listener(
    name: str | None = None, filter: _Callable | None = None, *, priority: int = 1
) -> _Callable: ...


def event_listener(
    name: Any = None, filter: _Callable | None = None, *, priority: int = 1
) -> Any:
    """Mark a function as an event listener.

    This decorator attaches metadata to the function, identifying it
    as a subscriber for the specified event.
    """

    def decorator(func: _EventCallbackT) -> _EventCallbackT:
        # Attach metadata to the function to mark it as a listener.
        event = (
            name
            if isinstance(name, str)
            else func.__qualname__.split("on_event_", 1)[1]
        )
        setattr(func, "_on_event", event)
        setattr(func, "_on_event_filter", filter)
        setattr(func, "_on_event_priority", priority)
        return func

    if callable(name):
        return decorator(name)
    else:
        return decorator


T = TypeVar("T")


class EventManager(TaskManager, Generic[T]):
    """Represents an event manager."""

    __slots__ = ("_data", "_events", "_listeners")

    _data: dict[str, T]
    _events: dict[str, asyncio.Event]
    _listeners: dict[str, set[EventListener]]

    def __init__(self) -> None:
        """Initialize a new event manager."""
        super().__init__()
        self._data = {}
        self._events = {}
        self._listeners = {}
        self._register_event_listeners()

    def __getattr__(self, name: str) -> T:
        """Return attributes from the underlying data dictionary."""
        try:
            return self.data[name]
        except KeyError as e:
            raise AttributeError from e

    def _register_event_listeners(self) -> None:
        """Register the event listeners."""
        for event, listener in self.event_listeners():
            filter_func = getattr(listener, "_on_event_filter", None)
            priority = getattr(listener, "_on_event_priority", 1)
            callback = filter_func(listener) if filter_func else listener
            self.subscribe(event, callback, priority=priority)

    def event_listeners(self) -> Generator[tuple[str, EventCallback]]:
        """Get the event listeners."""
        for _, listener in inspect.getmembers(self, predicate=inspect.ismethod):
            if event := getattr(listener, "_on_event", None):
                yield (event, listener)

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

    def subscribe(
        self, name: str, callback: _EventCallbackT, *, priority: int = 1
    ) -> _EventCallbackT:
        """Subscribe a listener to the event.

        :param name: Event name or ID
        :type name: str
        :param callback: A coroutine callback function, that will be
            awaited on the with the event data as an argument.
        :type callback: EventCallback
        :return: A reference to the callback, that can be used
            with `EventManager.unsubscribe()`.
        :rtype: EventCallback
        """
        listener = EventListener(callback, priority=priority)
        listeners = self._listeners.setdefault(name, set())
        listeners.add(listener)
        _LOGGER.debug(
            "Registered listener '%s' for event '%s' with priority %d",
            callback.__name__,
            name,
            priority,
        )
        return callback

    def subscribe_once(
        self, name: str, callback: EventCallback, *, priority: int = 1
    ) -> EventCallback:
        """Subscribe a listener to the event once.

        Callback will be unsubscribed after single event.

        :param name: Event name or ID
        :type name: str
        :param callback: A coroutine callback function, that will be
            awaited on the with the event data as an argument.
        :type callback: EventCallback
        :return: A reference to the callback, that can be used
            with `EventManager.unsubscribe()`.
        :rtype: EventCallback
        """

        async def _call_once(value: Any) -> Any:
            """Unsubscribe callback from the event and calls it."""
            self.unsubscribe(name, _call_once)
            return await callback(value)

        return self.subscribe(name, _call_once, priority=priority)

    def unsubscribe(self, name: str, callback: EventCallback) -> bool:
        """Usubscribe a callback from the event.

        :param name: Event name or ID
        :type name: str
        :param callback: A coroutine callback function, previously
            subscribed to an event using ``subscribe()`` or
            ``subscribe_once()`` methods.
        :type callback: EventCallback
        :return: `True` if callback is found, `False` otherwise.
        :rtype: bool
        """
        listener = EventListener(callback)
        if name in self._listeners and listener in self._listeners[name]:
            self._listeners[name].remove(listener)
            return True

        return False

    async def dispatch(self, name: str, value: T) -> None:
        """Call registered listeners and dispatch the event."""
        listeners = self._listeners.get(name, set())
        sorted_listeners = sorted(listeners, key=lambda listener: listener.priority)
        _LOGGER.debug("Dispatching event '%s' with %d listeners", name, len(listeners))
        for listener in sorted_listeners:
            callback = listener.callback
            _LOGGER.debug(
                "Executing listener '%s' with priority %d",
                callback.__name__,
                listener.priority,
            )
            try:
                if (result := await callback(value)) is not None:
                    value = result
            except Exception as e:
                _LOGGER.exception(
                    "Error in event listener %s: %s", callback.__name__, e
                )

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


__all__ = ["EventCallback", "EventManager", "event_listener"]
