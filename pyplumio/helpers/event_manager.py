"""Contains an event manager class."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine, Generator
import inspect
import logging
from types import MappingProxyType
from typing import Any, Generic, NewType, TypeAlias, TypeVar, overload

from pyplumio.helpers.task_manager import TaskManager

EventCallback: TypeAlias = Callable[..., Coroutine[Any, Any, Any]]
_FilterFunc: TypeAlias = Callable[[EventCallback], Any]

_EventCallbackT = TypeVar("_EventCallbackT", bound=EventCallback)

_LOGGER = logging.getLogger(__name__)


@overload
def event_listener(
    name: Callable[..., Any], filter: _FilterFunc | None = None
) -> EventCallback: ...


@overload
def event_listener(
    name: str | None = None, filter: _FilterFunc | None = None
) -> Callable[..., EventCallback]: ...


def event_listener(name: Any = None, filter: Any = None) -> Any:
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
        return func

    if callable(name):
        return decorator(name)
    else:
        return decorator


_EventDataT = TypeVar("_EventDataT")
_DefaultT = TypeVar("_DefaultT")

StopPropagationType = NewType("StopPropagationType", object)
StopPropagation = StopPropagationType(object())


class EventManager(TaskManager, Generic[_EventDataT]):
    """Represents an event manager."""

    __slots__ = ("_data", "_events", "_callbacks")

    _data: dict[str, _EventDataT]
    _events: dict[str, asyncio.Event]
    _callbacks: dict[str, list[EventCallback]]

    def __init__(self) -> None:
        """Initialize a new event manager."""
        super().__init__()
        self._data = {}
        self._events = {}
        self._callbacks = {}
        self._register_event_listeners()

    def __getattr__(self, name: str) -> _EventDataT:
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

    def event_listeners(self) -> Generator[tuple[str, EventCallback]]:
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

    async def get(self, name: str, timeout: float | None = None) -> _EventDataT:
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
    def get_nowait(self, name: str) -> _EventDataT: ...

    @overload
    def get_nowait(self, name: str, default: _DefaultT) -> _EventDataT | _DefaultT: ...

    def get_nowait(self, name: str, default: Any = None) -> Any:
        """Get the value by name without waiting.

        If value is not available, default value will be
        returned instead.

        :param name: Event name or ID
        :type name: str
        :param default: default value to return if data is unavailable,
            defaults to `None`
        :type default: _DefaultT, optional
        :return: An event data
        :rtype: _DataT | _DefaultT, optional
        """
        try:
            return self.data[name]
        except KeyError:
            return default

    def subscribe(self, name: str, callback: _EventCallbackT) -> _EventCallbackT:
        """Subscribe a callback to the event.

        :param name: Event name or ID
        :type name: str
        :param callback: A coroutine callback function, that will be
            awaited on the with the event data as an argument.
        :type callback: EventCallback
        :return: A reference to the callback, that can be used
            with `EventManager.unsubscribe()`.
        :rtype: EventCallback
        """
        callbacks = self._callbacks.setdefault(name, [])
        _LOGGER.debug(
            "Registered listener '%s' for event '%s'", callback.__name__, name
        )
        callbacks.append(callback)
        return callback

    def subscribe_once(self, name: str, callback: EventCallback) -> EventCallback:
        """Subscribe a callback to the event once.

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

        return self.subscribe(name, _call_once)

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
        if name in self._callbacks and callback in self._callbacks[name]:
            self._callbacks[name].remove(callback)
            return True

        return False

    async def dispatch(self, name: str, value: _EventDataT) -> None:
        """Call registered callbacks and dispatch the event."""
        callbacks = self._callbacks.get(name, [])
        for callback in list(callbacks):
            try:
                result = await callback(value)
            except Exception as e:
                _LOGGER.exception(
                    "Error in event listener %s: %s", callback.__name__, e
                )
                continue

            if result is None:
                continue
            elif result is StopPropagation:
                break
            else:
                value = result

        self._data[name] = value
        self.set_event(name)

    def dispatch_nowait(self, name: str, value: _EventDataT) -> None:
        """Call a registered callbacks and dispatch the event without waiting."""
        self.create_task(self.dispatch(name, value))

    async def load(self, data: dict[str, _EventDataT]) -> None:
        """Load event data."""
        await asyncio.gather(
            *(self.dispatch(name, value) for name, value in data.items())
        )

    def load_nowait(self, data: dict[str, _EventDataT]) -> None:
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
    def data(self) -> MappingProxyType[str, _EventDataT]:
        """Return the event data."""
        return MappingProxyType(self._data)


__all__ = [
    "event_listener",
    "EventCallback",
    "EventManager",
    "StopPropagation",
    "StopPropagationType",
]
