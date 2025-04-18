"""Contains callback filters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from copy import copy
import math
import time
from typing import (
    Any,
    Final,
    Protocol,
    SupportsFloat,
    TypeVar,
    overload,
    runtime_checkable,
)

from pyplumio.helpers.event_manager import Callback
from pyplumio.helpers.parameter import Parameter

UNDEFINED: Final = "undefined"
TOLERANCE: Final = 0.1


@runtime_checkable
class SupportsSubtraction(Protocol):
    """Supports subtraction operation."""

    __slots__ = ()

    def __sub__(
        self: SupportsSubtraction, other: SupportsSubtraction
    ) -> SupportsSubtraction:
        """Subtract a value."""


@runtime_checkable
class SupportsComparison(Protocol):
    """Supports comparison."""

    __slots__ = ()

    def __eq__(self: SupportsComparison, other: SupportsComparison) -> bool:
        """Compare a value."""


Comparable = TypeVar("Comparable", Parameter, SupportsFloat, SupportsComparison)


@overload
def is_close(old: Parameter, new: Parameter) -> bool: ...


@overload
def is_close(old: SupportsFloat, new: SupportsFloat) -> bool: ...


@overload
def is_close(old: SupportsComparison, new: SupportsComparison) -> bool: ...


def is_close(old: Comparable, new: Comparable) -> bool:
    """Check if value is significantly changed."""
    if isinstance(old, Parameter) and isinstance(new, Parameter):
        return new.pending_update or old.values.__ne__(new.values)

    if isinstance(old, SupportsFloat) and isinstance(new, SupportsFloat):
        return not math.isclose(old, new, abs_tol=TOLERANCE)

    return old.__ne__(new)


@overload
def diffence_between(old: list, new: list) -> list: ...


@overload
def diffence_between(
    old: SupportsSubtraction, new: SupportsSubtraction
) -> SupportsSubtraction: ...


def diffence_between(
    old: SupportsSubtraction | list, new: SupportsSubtraction | list
) -> SupportsSubtraction | list | None:
    """Return a difference between values."""
    if isinstance(old, list) and isinstance(new, list):
        return [x for x in new if x not in old]

    if isinstance(old, SupportsSubtraction) and isinstance(new, SupportsSubtraction):
        return new.__sub__(old)

    return None


class Filter(ABC):
    """Represents a filter."""

    __slots__ = ("_callback", "_value")

    _callback: Callback
    _value: Any

    def __init__(self, callback: Callback) -> None:
        """Initialize a new filter."""
        self._callback = callback
        self._value = UNDEFINED

    def __eq__(self, other: Any) -> bool:
        """Compare callbacks."""
        if isinstance(other, Filter):
            return self._callback == other._callback

        if callable(other):
            return bool(self._callback == other)

        return NotImplemented

    @abstractmethod
    async def __call__(self, new_value: Any) -> Any:
        """Set a new value for the callback."""


class Clamp(Filter):
    """Represents a clamp filter.

    Calls callback with a value clamped between specified boundaries.
    """

    __slots__ = ("_min_value", "_max_value")

    _min_value: float
    _max_value: float

    def __init__(self, callback: Callback, min_value: float, max_value: float) -> None:
        """Initialize a new Clamp filter.

        A callback function will be called and passed value clamped
        between specified boundaries.

        :param callback: A callback function to be awaited on new value
        :type callback: Callback
        :param min_value: A lower boundary
        :type min_value: float
        :param max_value: An upper boundary
        :type max_value: float
        :return: An instance of callable filter
        :rtype: Clamp
        """
        super().__init__(callback)
        self._min_value = min_value
        self._max_value = max_value

    async def __call__(self, new_value: Any) -> Any:
        """Set a new value for the callback."""
        if new_value < self._min_value:
            return await self._callback(self._min_value)

        if new_value > self._max_value:
            return await self._callback(self._max_value)

        return await self._callback(new_value)


class OnChange(Filter):
    """Represents a value changed filter.

    Calls a callback only when value is changed from the
    previous callback call.
    """

    __slots__ = ()

    def __init__(self, callback: Callback) -> None:
        """Initialize a new value changed filter.

        A callback function will only be called if value is changed from the
        previous call.

        :param callback: A callback function to be awaited on value change
        :type callback: Callback
        :return: An instance of callable filter
        :rtype: OnChange
        """
        super().__init__(callback)

    async def __call__(self, new_value: Any) -> Any:
        """Set a new value for the callback."""
        if self._value == UNDEFINED or is_close(self._value, new_value):
            self._value = (
                copy(new_value) if isinstance(new_value, Parameter) else new_value
            )
            return await self._callback(new_value)


class Debounce(Filter):
    """Represents a debounce filter.

    Calls a callback only when value is stabilized across multiple
    filter calls.
    """

    __slots__ = ("_calls", "_min_calls")

    _calls: int
    _min_calls: int

    def __init__(self, callback: Callback, min_calls: int) -> None:
        """Initialize a new debounce filter.

        A callback function will only called once value is stabilized
        across multiple filter calls.

        :param callback: A callback function to be awaited on value change
        :type callback: Callback
        :param min_calls: Value shouldn't change for this amount of
            filter calls
        :type min_calls: int
        :return: An instance of callable filter
        :rtype: Debounce
        """
        super().__init__(callback)
        self._calls = 0
        self._min_calls = min_calls

    async def __call__(self, new_value: Any) -> Any:
        """Set a new value for the callback."""
        if self._value == UNDEFINED or is_close(self._value, new_value):
            self._calls += 1
        else:
            self._calls = 0

        if self._value == UNDEFINED or self._calls >= self._min_calls:
            self._value = (
                copy(new_value) if isinstance(new_value, Parameter) else new_value
            )
            self._calls = 0
            return await self._callback(new_value)


class Throttle(Filter):
    """Represents a throttle filter.

    Calls a callback only when certain amount of seconds passed
    since the last call.
    """

    __slots__ = ("_last_called", "_timeout")

    _last_called: float | None
    _timeout: float

    def __init__(self, callback: Callback, seconds: float) -> None:
        """Initialize a new throttle filter.

        A callback function will only be called once a certain amount of
        seconds passed since the last call.

        :param callback: A callback function that will be awaited once
            filter conditions are fulfilled
        :type callback: Callback
        :param seconds: A callback will be awaited at most once per
            this amount of seconds
        :type seconds: float
        :return: An instance of callable filter
        :rtype: Throttle
        """
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


class Delta(Filter):
    """Represents a difference filter.

    Calls a callback with a difference between two subsequent values.
    """

    __slots__ = ()

    def __init__(self, callback: Callback) -> None:
        """Initialize a new difference filter.

        A callback function will be called with a difference between two
        subsequent value.

        :param callback: A callback function that will be awaited with
            difference between values in two subsequent calls
        :type callback: Callback
        :return: An instance of callable filter
        :rtype: Delta
        """
        super().__init__(callback)

    async def __call__(self, new_value: Any) -> Any:
        """Set a new value for the callback."""
        if self._value == UNDEFINED or is_close(self._value, new_value):
            old_value = self._value
            self._value = (
                copy(new_value) if isinstance(new_value, Parameter) else new_value
            )
            if (
                self._value != UNDEFINED
                and (difference := diffence_between(old_value, new_value)) is not None
            ):
                return await self._callback(difference)


class Aggregate(Filter):
    """Represents an aggregate filter.

    Calls a callback with a sum of values collected over a specified
    time period.
    """

    __slots__ = ("_sum", "_last_update", "_timeout")

    _sum: complex
    _last_update: float
    _timeout: float

    def __init__(self, callback: Callback, seconds: float) -> None:
        """Initialize a new aggregate filter.

        A callback function will be called with a sum of values collected
        over a specified time period. Can only be used with numeric values.

        :param callback: A callback function to be awaited once filter
            conditions are fulfilled
        :type callback: Callback
        :param seconds: A callback will be awaited with a sum of values
            aggregated over this amount of seconds.
        :type seconds: float
        :return: An instance of callable filter
        :rtype: Aggregate
        """
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


class Custom(Filter):
    """Represents a custom filter.

    Calls a callback with value, if user-defined filter function
    that's called by this class with the value as an argument
    returns true.
    """

    __slots__ = ("_filter_fn",)

    _filter_fn: Callable[[Any], bool]

    def __init__(self, callback: Callback, filter_fn: Callable[[Any], bool]) -> None:
        """Initialize a new custom filter.

        A callback function will be called when user-defined filter
        function, that's being called with the value as an argument,
        returns true.

        :param callback: A callback function to be awaited when
            filter function return true
        :type callback: Callback
        :param filter_fn: Filter function, that will be called with a
            value and should return `True` to await filter's callback
        :type filter_fn: Callable[[Any], bool]
        :return: An instance of callable filter
        :rtype: Custom
        """
        super().__init__(callback)
        self._filter_fn = filter_fn

    async def __call__(self, new_value: Any) -> Any:
        """Set a new value for the callback."""
        if self._filter_fn(new_value):
            await self._callback(new_value)


__all__ = [
    "Filter",
    "Clamp",
    "OnChange",
    "Debounce",
    "Throttle",
    "Delta",
    "Aggregate",
    "Custom",
]
