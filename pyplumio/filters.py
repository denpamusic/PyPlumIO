"""Contains callback filters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import suppress
from copy import copy
from decimal import Decimal
import logging
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

from typing_extensions import TypeAlias

from pyplumio.helpers.event_manager import Callback
from pyplumio.parameters import Parameter

_LOGGER = logging.getLogger(__name__)

numpy_installed = False
with suppress(ImportError):
    import numpy as np

    _LOGGER.info("Using numpy for improved float precision")
    numpy_installed = True


UNDEFINED: Final = "undefined"


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

    def __hash__(self) -> int:
        """Return a hash of the value."""

    def __eq__(self: SupportsComparison, other: SupportsComparison) -> bool:
        """Compare a value."""


Comparable = TypeVar("Comparable", Parameter, SupportsFloat, SupportsComparison)

DEFAULT_TOLERANCE: Final = 1e-6


@overload
def is_close(old: Parameter, new: Parameter, tolerance: None = None) -> bool: ...


@overload
def is_close(
    old: SupportsFloat, new: SupportsFloat, tolerance: float = DEFAULT_TOLERANCE
) -> bool: ...


@overload
def is_close(
    old: SupportsComparison, new: SupportsComparison, tolerance: None = None
) -> bool: ...


def is_close(
    old: Comparable, new: Comparable, tolerance: float | None = DEFAULT_TOLERANCE
) -> bool:
    """Check if value is significantly changed."""
    if isinstance(old, Parameter) and isinstance(new, Parameter):
        return new.update_pending.is_set() or old.values.__ne__(new.values)

    if tolerance and isinstance(old, SupportsFloat) and isinstance(new, SupportsFloat):
        return not math.isclose(old, new, abs_tol=tolerance)

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

    def __hash__(self) -> int:
        """Return a hash of the filter based on its callback."""
        return hash(self._callback)

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


class _Aggregate(Filter):
    """Represents an aggregate filter.

    Calls a callback with a sum of values collected over a specified
    time period or when sample size limit reached.
    """

    __slots__ = ("_values", "_sample_size", "_timeout", "_last_call_time")

    _values: list[float | int | Decimal]
    _sample_size: int
    _timeout: float
    _last_call_time: float

    def __init__(self, callback: Callback, seconds: float, sample_size: int) -> None:
        """Initialize a new aggregate filter."""
        super().__init__(callback)
        self._last_call_time = time.monotonic()
        self._timeout = seconds
        self._sample_size = sample_size
        self._values = []

    async def __call__(self, new_value: Any) -> Any:
        """Set a new value for the callback."""
        if not isinstance(new_value, (float, int, Decimal)):
            raise TypeError(
                "Aggregate filter can only be used with numeric values, got "
                f"{type(new_value).__name__}: {new_value}"
            )

        current_time = time.monotonic()
        self._values.append(new_value)
        time_since_call = current_time - self._last_call_time
        if time_since_call >= self._timeout or len(self._values) >= self._sample_size:
            result = await self._callback(
                np.sum(self._values) if numpy_installed else sum(self._values)
            )
            self._last_call_time = current_time
            self._values = []
            return result


def aggregate(callback: Callback, seconds: float, sample_size: int) -> _Aggregate:
    """Create a new aggregate filter.

    A callback function will be called with a sum of values collected
    over a specified time period or when sample size limit reached.
    Can only be used with numeric values.

    :param callback: A callback function to be awaited once filter
        conditions are fulfilled
    :type callback: Callback
    :param seconds: A callback will be awaited with a sum of values
        aggregated over this amount of seconds.
    :type seconds: float
    :param sample_size: The maximum number of values to aggregate
        before calling the callback
    :type sample_size: int
    :return: An instance of callable filter
    :rtype: _Aggregate
    """
    return _Aggregate(callback, seconds, sample_size)


class _Clamp(Filter):
    """Represents a clamp filter.

    Calls callback with a value clamped between specified boundaries.
    """

    __slots__ = ("_min_value", "_max_value")

    _min_value: float
    _max_value: float

    def __init__(self, callback: Callback, min_value: float, max_value: float) -> None:
        """Initialize a new Clamp filter."""
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


def clamp(callback: Callback, min_value: float, max_value: float) -> _Clamp:
    """Create a new clamp filter.

    A callback function will be called and passed value clamped
    between specified boundaries.

    :param callback: A callback function to be awaited on new value
    :type callback: Callback
    :param min_value: A lower boundary
    :type min_value: float
    :param max_value: An upper boundary
    :type max_value: float
    :return: An instance of callable filter
    :rtype: _Clamp
    """
    return _Clamp(callback, min_value, max_value)


_FilterT: TypeAlias = Callable[[Any], bool]


class _Custom(Filter):
    """Represents a custom filter.

    Calls a callback with value, if user-defined filter function
    that's called by this class with the value as an argument
    returns true.
    """

    __slots__ = ("_filter_fn",)

    _filter_fn: _FilterT

    def __init__(self, callback: Callback, filter_fn: _FilterT) -> None:
        """Initialize a new custom filter."""
        super().__init__(callback)
        self._filter_fn = filter_fn

    async def __call__(self, new_value: Any) -> Any:
        """Set a new value for the callback."""
        if self._filter_fn(new_value):
            await self._callback(new_value)


def custom(callback: Callback, filter_fn: _FilterT) -> _Custom:
    """Create a new custom filter.

    A callback function will be called when a user-defined filter
    function, that's being called with the value as an argument,
    returns true.

    :param callback: A callback function to be awaited when
        filter function return true
    :type callback: Callback
    :param filter_fn: Filter function, that will be called with a
        value and should return `True` to await filter's callback
    :type filter_fn: Callable[[Any], bool]
    :return: An instance of callable filter
    :rtype: _Custom
    """
    return _Custom(callback, filter_fn)


class _Deadband(Filter):
    """Represents a deadband filter.

    Calls a callback only when value is significantly changed from the
    previous callback call.
    """

    __slots__ = ("_tolerance",)

    _tolerance: float

    def __init__(self, callback: Callback, tolerance: float) -> None:
        """Initialize a new value changed filter."""
        self._tolerance = tolerance
        super().__init__(callback)

    async def __call__(self, new_value: Any) -> Any:
        """Set a new value for the callback."""
        if not isinstance(new_value, (float, int, Decimal)):
            raise TypeError(
                "Deadband filter can only be used with numeric values, got "
                f"{type(new_value).__name__}: {new_value}"
            )

        if self._value == UNDEFINED or is_close(
            self._value, new_value, tolerance=self._tolerance
        ):
            self._value = new_value
            return await self._callback(new_value)


def deadband(callback: Callback, tolerance: float) -> _Deadband:
    """Create a new deadband filter.

    A callback function will only be called when the value is significantly changed
    from the previous callback call.

    :param callback: A callback function to be awaited on significant value change
    :type callback: Callback
    :param tolerance: The minimum difference required to trigger the callback
    :type tolerance: float
    :return: An instance of callable filter
    :rtype: _Deadband
    """
    return _Deadband(callback, tolerance)


class _Debounce(Filter):
    """Represents a debounce filter.

    Calls a callback only when value is stabilized across multiple
    filter calls.
    """

    __slots__ = ("_calls", "_min_calls")

    _calls: int
    _min_calls: int

    def __init__(self, callback: Callback, min_calls: int) -> None:
        """Initialize a new debounce filter."""
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


def debounce(callback: Callback, min_calls: int) -> _Debounce:
    """Create a new debounce filter.

    A callback function will only be called once the value is stabilized
    across multiple filter calls.

    :param callback: A callback function to be awaited on value change
    :type callback: Callback
    :param min_calls: Value shouldn't change for this amount of
        filter calls
    :type min_calls: int
    :return: An instance of callable filter
    :rtype: _Debounce
    """
    return _Debounce(callback, min_calls)


class _Delta(Filter):
    """Represents a difference filter.

    Calls a callback with a difference between two subsequent values.
    """

    __slots__ = ()

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


def delta(callback: Callback) -> _Delta:
    """Create a new difference filter.

    A callback function will be called with a difference between two
    subsequent values.

    :param callback: A callback function that will be awaited with
        difference between values in two subsequent calls
    :type callback: Callback
    :return: An instance of callable filter
    :rtype: _Delta
    """
    return _Delta(callback)


class _OnChange(Filter):
    """Represents a value changed filter.

    Calls a callback only when value is changed from the
    previous callback call.
    """

    __slots__ = ()

    def __init__(self, callback: Callback) -> None:
        """Initialize a new value changed filter."""
        super().__init__(callback)

    async def __call__(self, new_value: Any) -> Any:
        """Set a new value for the callback."""
        if self._value == UNDEFINED or is_close(self._value, new_value):
            self._value = (
                copy(new_value) if isinstance(new_value, Parameter) else new_value
            )
            return await self._callback(new_value)


def on_change(callback: Callback) -> _OnChange:
    """Create a new value changed filter.

    A callback function will only be called if the value is changed from the
    previous call.

    :param callback: A callback function to be awaited on value change
    :type callback: Callback
    :return: An instance of callable filter
    :rtype: _OnChange
    """
    return _OnChange(callback)


class _Throttle(Filter):
    """Represents a throttle filter.

    Calls a callback only when certain amount of seconds passed
    since the last call.
    """

    __slots__ = ("_last_called", "_timeout")

    _last_called: float | None
    _timeout: float

    def __init__(self, callback: Callback, seconds: float) -> None:
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


def throttle(callback: Callback, seconds: float) -> _Throttle:
    """Create a new throttle filter.

    A callback function will only be called once a certain amount of
    seconds passed since the last call.

    :param callback: A callback function that will be awaited once
        filter conditions are fulfilled
    :type callback: Callback
    :param seconds: A callback will be awaited at most once per
        this amount of seconds
    :type seconds: float
    :return: An instance of callable filter
    :rtype: _Throttle
    """
    return _Throttle(callback, seconds)


__all__ = [
    "Filter",
    "aggregate",
    "clamp",
    "custom",
    "deadband",
    "debounce",
    "delta",
    "on_change",
    "throttle",
]
