"""Contains callback filters."""
from __future__ import annotations

from abc import ABC, abstractmethod
import math
import time
from typing import Any, Final, SupportsFloat, overload

from pyplumio.const import UNDEFINED
from pyplumio.helpers.parameter import Parameter
from pyplumio.helpers.typing import EventCallbackType, SupportsSubtraction

TOLERANCE: Final = 0.1


@overload
def _significantly_changed(old: Parameter, new: Parameter) -> bool:
    """Check if parameter is significantly changed."""


@overload
def _significantly_changed(old: SupportsFloat, new: SupportsFloat) -> bool:
    """Check if float value is significantly changed."""


def _significantly_changed(old, new) -> bool:
    """Check if value is significantly changed."""
    if old == UNDEFINED or (hasattr(old, "is_changed") and old.is_changed):
        return True

    if isinstance(old, Parameter) and isinstance(new, Parameter):
        return (
            old.value != new.value
            or old.min_value != new.min_value
            or old.max_value != new.max_value
        )

    try:
        result = not math.isclose(old, new, abs_tol=TOLERANCE)
    except TypeError:
        result = old != new

    return result


@overload
def _diffence_between(old: list, new: list) -> list:
    """Return a difference between lists."""


@overload
def _diffence_between(old: SupportsSubtraction, new: SupportsSubtraction) -> list:
    """Return a difference between substractable."""


def _diffence_between(old, new):
    """Return a difference between values."""
    if old == UNDEFINED:
        return None

    if isinstance(old, list) and isinstance(new, list):
        return [x for x in new if x not in old]

    if hasattr(old, "__sub__") and hasattr(new, "__sub__"):
        return new - old

    return None


class Filter(ABC):
    """Represents a filter."""

    _callback: Any
    _value: Any = UNDEFINED

    def __init__(self, callback: EventCallbackType):
        """Initialize a new filter."""
        self._callback = callback
        self._value = UNDEFINED

    def __eq__(self, other) -> bool:
        """Compare callbacks."""
        if isinstance(other, Filter):
            return self._callback == other._callback

        if callable(other):
            return self._callback == other

        raise TypeError

    @abstractmethod
    async def __call__(self, new_value):
        """Set a new value for the callback."""


class _OnChange(Filter):
    """Represents a value changed filter.

    Calls a callback only when value is changed from the
    previous callback call.
    """

    async def __call__(self, new_value):
        """Set a new value for the callback."""
        if _significantly_changed(self._value, new_value):
            self._value = new_value
            return await self._callback(new_value)


def on_change(callback: EventCallbackType) -> _OnChange:
    """
    A value changed filter.

    A callback function will only be called if value is changed from the
    previous call.
    """
    return _OnChange(callback)


class _Debounce(Filter):
    """Represents a debounce filter.

    Calls a callback only when value is stabilized across multiple
    filter calls.
    """

    _calls: int = 0
    _min_calls: int = 3

    def __init__(self, callback: EventCallbackType, min_calls: int):
        """Initialize a new debounce filter."""
        super().__init__(callback)
        self._calls = 0
        self._min_calls = min_calls

    async def __call__(self, new_value):
        """Set a new value for the callback."""
        if _significantly_changed(self._value, new_value):
            self._calls += 1
        else:
            self._calls = 0

        if self._value == UNDEFINED or self._calls >= self._min_calls:
            self._value = new_value
            self._calls = 0
            return await self._callback(new_value)


def debounce(callback: EventCallbackType, min_calls) -> _Debounce:
    """A debounce filter.

    A callback function will only called once value is stabilized
    across multiple filter calls.
    """
    return _Debounce(callback, min_calls)


class _Throttle(Filter):
    """Represents a throttle filter.

    Calls a callback only when certain amount of seconds passed
    since the last call.
    """

    _last_called: float | None
    _timeout: float

    def __init__(self, callback: EventCallbackType, seconds: float):
        """Initialize a new throttle filter."""
        super().__init__(callback)
        self._last_called = None
        self._timeout = seconds

    async def __call__(self, new_value):
        """Set a new value for the callback."""
        current_timestamp = time.monotonic()
        if (
            self._last_called is None
            or (current_timestamp - self._last_called) >= self._timeout
        ):
            self._last_called = current_timestamp
            return await self._callback(new_value)


def throttle(callback: EventCallbackType, seconds: float) -> _Throttle:
    """A throttle filter.

    A callback function will only be called once a certain amount of
    seconds passed since the last call.
    """
    return _Throttle(callback, seconds)


class _Delta(Filter):
    """Represents a difference filter.

    Calls a callback with a difference between two subsequent values.
    """

    async def __call__(self, new_value):
        """Set a new value for the callback."""
        if _significantly_changed(self._value, new_value):
            old_value = self._value
            self._value = new_value
            if (difference := _diffence_between(old_value, new_value)) is not None:
                return await self._callback(difference)


def delta(callback: EventCallbackType) -> _Delta:
    """A difference filter.

    A callback function will be called with a difference between two
    subsequent value.
    """
    return _Delta(callback)


class _Aggregate(Filter):
    """Represents an aggregate filter.

    Calls a callback with a sum of values collected over a specified
    time period.
    """

    _sum: complex
    _last_update: float | None
    _timeout: float

    def __init__(self, callback: EventCallbackType, seconds: float):
        """Initialize a new aggregate filter."""
        super().__init__(callback)
        self._last_update = time.monotonic()
        self._timeout = seconds
        self._sum = 0.0

    async def __call__(self, new_value):
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


def aggregate(callback: EventCallbackType, seconds: float) -> _Aggregate:
    """An aggregate filter.

    A callback function will be called with a sum of values collected
    over a specified time period.
    """
    return _Aggregate(callback, seconds)
