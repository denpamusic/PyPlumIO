"""Contains callback filters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from copy import copy
import math
import time
from typing import Any, Final, SupportsFloat, TypeVar, overload

from pyplumio.helpers.parameter import Parameter
from pyplumio.helpers.typing import SupportsComparison, SupportsSubtraction

UNDEFINED: Final = "undefined"
TOLERANCE: Final = 0.1

Comparable = TypeVar("Comparable", Parameter, SupportsFloat, SupportsComparison)


@overload
def _significantly_changed(old: Parameter, new: Parameter) -> bool: ...


@overload
def _significantly_changed(old: SupportsFloat, new: SupportsFloat) -> bool: ...


@overload
def _significantly_changed(
    old: SupportsComparison, new: SupportsComparison
) -> bool: ...


def _significantly_changed(old: Comparable, new: Comparable) -> bool:
    """Check if value is significantly changed."""
    if isinstance(old, Parameter) and isinstance(new, Parameter):
        result = new.pending_update or old.values != new.values
    elif isinstance(old, SupportsFloat) and isinstance(new, SupportsFloat):
        result = not math.isclose(old, new, abs_tol=TOLERANCE)
    else:
        result = old != new

    return result


@overload
def _diffence_between(old: list, new: list) -> list: ...


@overload
def _diffence_between(
    old: SupportsSubtraction, new: SupportsSubtraction
) -> SupportsSubtraction: ...


def _diffence_between(
    old: SupportsSubtraction | list, new: SupportsSubtraction | list
) -> SupportsSubtraction | list | None:
    """Return a difference between values."""
    if isinstance(old, list) and isinstance(new, list):
        return [x for x in new if x not in old]
    elif isinstance(old, SupportsSubtraction) and isinstance(new, SupportsSubtraction):
        return new - old
    else:
        return None


class Filter(ABC):
    """Represents a filter."""

    __slots__ = ("_callback", "_value")

    _callback: Callable[[Any], Awaitable[Any]]
    _value: Any

    def __init__(self, callback: Callable[[Any], Awaitable[Any]]) -> None:
        """Initialize a new filter."""
        self._callback = callback
        self._value = UNDEFINED

    def __eq__(self, other: Any) -> Any:
        """Compare callbacks."""
        if isinstance(other, Filter):
            return self._callback == other._callback

        if callable(other):
            return self._callback == other

        return NotImplemented

    @abstractmethod
    async def __call__(self, new_value: Any) -> Any:
        """Set a new value for the callback."""


class _OnChange(Filter):
    """Represents a value changed filter.

    Calls a callback only when value is changed from the
    previous callback call.
    """

    __slots__ = ()

    async def __call__(self, new_value: Any) -> Any:
        """Set a new value for the callback."""
        if self._value == UNDEFINED or _significantly_changed(self._value, new_value):
            self._value = (
                copy(new_value) if isinstance(new_value, Parameter) else new_value
            )
            return await self._callback(new_value)


def on_change(callback: Callable[[Any], Awaitable[Any]]) -> _OnChange:
    """Return a value changed filter.

    A callback function will only be called if value is changed from the
    previous call.

    :param callback: A callback function to be awaited on value change
    :type callback: Callable[[Any], Awaitable[Any]]
    :return: A instance of callable filter
    :rtype: _OnChange
    """
    return _OnChange(callback)


class _Debounce(Filter):
    """Represents a debounce filter.

    Calls a callback only when value is stabilized across multiple
    filter calls.
    """

    __slots__ = ("_calls", "_min_calls")

    _calls: int
    _min_calls: int

    def __init__(
        self, callback: Callable[[Any], Awaitable[Any]], min_calls: int
    ) -> None:
        """Initialize a new debounce filter."""
        super().__init__(callback)
        self._calls = 0
        self._min_calls = min_calls

    async def __call__(self, new_value: Any) -> Any:
        """Set a new value for the callback."""
        if self._value == UNDEFINED or _significantly_changed(self._value, new_value):
            self._calls += 1
        else:
            self._calls = 0

        if self._value == UNDEFINED or self._calls >= self._min_calls:
            self._value = (
                copy(new_value) if isinstance(new_value, Parameter) else new_value
            )
            self._calls = 0
            return await self._callback(new_value)


def debounce(callback: Callable[[Any], Awaitable[Any]], min_calls: int) -> _Debounce:
    """Return a debounce filter.

    A callback function will only called once value is stabilized
    across multiple filter calls.

    :param callback: A callback function to be awaited on value change
    :type callback: Callable[[Any], Awaitable[Any]]
    :param min_calls: Value shouldn't change for this amount of
        filter calls
    :type min_calls: int
    :return: A instance of callable filter
    :rtype: _Debounce
    """
    return _Debounce(callback, min_calls)


class _Throttle(Filter):
    """Represents a throttle filter.

    Calls a callback only when certain amount of seconds passed
    since the last call.
    """

    __slots__ = ("_last_called", "_timeout")

    _last_called: float | None
    _timeout: float

    def __init__(
        self, callback: Callable[[Any], Awaitable[Any]], seconds: float
    ) -> None:
        """Initialize a new throttle filter."""
        super().__init__(callback)
        self._last_called = None
        self._timeout = seconds

    async def __call__(self, new_value: Any) -> Any:
        """Set a new value for the callback."""
        current_timestamp = time.monotonic()
        if (
            self._last_called is None
            or (current_timestamp - self._last_called) >= self._timeout
        ):
            self._last_called = current_timestamp
            return await self._callback(new_value)


def throttle(callback: Callable[[Any], Awaitable[Any]], seconds: float) -> _Throttle:
    """Return a throttle filter.

    A callback function will only be called once a certain amount of
    seconds passed since the last call.

    :param callback: A callback function that will be awaited once
        filter conditions are fulfilled
    :type callback: Callable[[Any], Awaitable[Any]]
    :param seconds: A callback will be awaited at most once per
        this amount of seconds
    :type seconds: float
    :return: A instance of callable filter
    :rtype: _Throttle
    """
    return _Throttle(callback, seconds)


class _Delta(Filter):
    """Represents a difference filter.

    Calls a callback with a difference between two subsequent values.
    """

    __slots__ = ()

    async def __call__(self, new_value: Any) -> Any:
        """Set a new value for the callback."""
        if self._value == UNDEFINED or _significantly_changed(self._value, new_value):
            old_value = self._value
            self._value = (
                copy(new_value) if isinstance(new_value, Parameter) else new_value
            )
            if (
                self._value != UNDEFINED
                and (difference := _diffence_between(old_value, new_value)) is not None
            ):
                return await self._callback(difference)


def delta(callback: Callable[[Any], Awaitable[Any]]) -> _Delta:
    """Return a difference filter.

    A callback function will be called with a difference between two
    subsequent value.

    :param callback: A callback function that will be awaited with
        difference between values in two subsequent calls
    :type callback: Callable[[Any], Awaitable[Any]]
    :return: A instance of callable filter
    :rtype: _Delta
    """
    return _Delta(callback)


class _Aggregate(Filter):
    """Represents an aggregate filter.

    Calls a callback with a sum of values collected over a specified
    time period.
    """

    __slots__ = ("_sum", "_last_update", "_timeout")

    _sum: complex
    _last_update: float
    _timeout: float

    def __init__(
        self, callback: Callable[[Any], Awaitable[Any]], seconds: float
    ) -> None:
        """Initialize a new aggregate filter."""
        super().__init__(callback)
        self._last_update = time.monotonic()
        self._timeout = seconds
        self._sum = 0.0

    async def __call__(self, new_value: Any) -> Any:
        """Set a new value for the callback."""
        current_timestamp = time.monotonic()
        try:
            self._sum += new_value
        except TypeError as e:
            raise ValueError(
                "Aggregate filter can only be used with numeric values"
            ) from e

        if current_timestamp - self._last_update >= self._timeout:
            result = await self._callback(self._sum)
            self._last_update = current_timestamp
            self._sum = 0.0
            return result


def aggregate(callback: Callable[[Any], Awaitable[Any]], seconds: float) -> _Aggregate:
    """Return an aggregate filter.

    A callback function will be called with a sum of values collected
    over a specified time period. Can only be used with numeric values.

    :param callback: A callback function to be awaited once filter
        conditions are fulfilled
    :type callback: Callable[[Any], Awaitable[Any]]
    :param seconds: A callback will be awaited with a sum of values
        aggregated over this amount of seconds.
    :type seconds: float
    :return: A instance of callable filter
    :rtype: _Aggregate
    """
    return _Aggregate(callback, seconds)


class _Custom(Filter):
    """Represents a custom filter.

    Calls a callback with value, if user-defined filter function
    that's called by this class with the value as an argument
    returns true.
    """

    __slots__ = ("_filter_fn",)

    filter_fn: Callable[[Any], bool]

    def __init__(
        self,
        callback: Callable[[Any], Awaitable[Any]],
        filter_fn: Callable[[Any], bool],
    ) -> None:
        """Initialize a new custom filter."""
        super().__init__(callback)
        self._filter_fn = filter_fn

    async def __call__(self, new_value: Any) -> Any:
        """Set a new value for the callback."""
        if self._filter_fn(new_value):
            await self._callback(new_value)


def custom(
    callback: Callable[[Any], Awaitable[Any]], filter_fn: Callable[[Any], bool]
) -> _Custom:
    """Return a custom filter.

    A callback function will be called when user-defined filter
    function, that's being called with the value as an argument,
    returns true.

    :param callback: A callback function to be awaited when
        filter function return true
    :type callback: Callable[[Any], Awaitable[Any]]
    :param filter_fn: Filter function, that will be called with a
        value and should return `True` to await filter's callback
    :type filter_fn: Callable[[Any], bool]
    :return: A instance of callable filter
    :rtype: _Custom
    """
    return _Custom(callback, filter_fn)
