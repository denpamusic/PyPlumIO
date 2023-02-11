"""Contains callback filters."""
from __future__ import annotations

from abc import ABC, abstractmethod
import decimal
import math
import time
from typing import Any, Final

from pyplumio.helpers.parameter import Parameter
from pyplumio.helpers.typing import EventCallbackType, NumericType

TOLERANCE: Final = 0.1

decimal.getcontext().prec = 12


def _significantly_changed(old_value, new_value) -> bool:
    """Check if value is significantly changed."""
    if old_value is None or (isinstance(old_value, Parameter) and old_value.is_changed):
        return True

    try:
        return not math.isclose(old_value, new_value, abs_tol=TOLERANCE)
    except TypeError:
        pass

    return old_value != new_value


def _diffence_between(old_value, new_value):
    """Return the difference between values."""
    if isinstance(old_value, list) and isinstance(new_value, list):
        return [x for x in new_value if x not in old_value]

    if hasattr(old_value, "__sub__") and hasattr(new_value, "__sub__"):
        return new_value - old_value

    return None


class Filter(ABC):
    """Represents base for value callback modifiers."""

    _callback: Any
    _value: Any

    def __init__(self, callback: EventCallbackType):
        """Initialize new Filter object."""
        self._callback = callback
        self._value = None

    def __eq__(self, other) -> bool:
        """Compare debounced callbacks."""
        if isinstance(other, Filter):
            return self._callback == other._callback

        if callable(other):
            return self._callback == other

        raise TypeError

    @abstractmethod
    async def __call__(self, new_value):
        """Set new value for the callback."""


class _OnChange(Filter):
    """Provides changed functionality to the callback."""

    async def __call__(self, new_value):
        """Set new value for the callback."""
        if _significantly_changed(self._value, new_value):
            self._value = new_value
            return await self._callback(new_value)


def on_change(callback: EventCallbackType) -> _OnChange:
    """Helper for change callback filter."""
    return _OnChange(callback)


class _Debounce(Filter):
    """Provides debounce functionality to the callback."""

    _calls: int = 0
    _min_calls: int = 3

    def __init__(self, callback: EventCallbackType, min_calls: int):
        """Initialize Debounce object."""
        super().__init__(callback)
        self._calls = 0
        self._min_calls = min_calls

    async def __call__(self, new_value):
        """Set new value for the callback."""
        if _significantly_changed(self._value, new_value):
            self._calls += 1
        else:
            self._calls = 0

        if self._calls >= self._min_calls or self._value is None:
            self._value = new_value
            self._calls = 0
            return await self._callback(new_value)


def debounce(callback: EventCallbackType, min_calls) -> _Debounce:
    """Helper method for debounce callback filter."""
    return _Debounce(callback, min_calls)


class _Throttle(Filter):
    """Provides throttle functionality to the callback."""

    _last_called: float | None
    _timeout: float

    def __init__(self, callback: EventCallbackType, seconds: float):
        """Initialize Debounce object."""
        super().__init__(callback)
        self._last_called = None
        self._timeout = seconds

    async def __call__(self, new_value):
        """set new value for the callback."""
        current_timestamp = time.monotonic()
        if (
            self._last_called is None
            or (current_timestamp - self._last_called) >= self._timeout
        ):
            self._last_called = current_timestamp
            return await self._callback(new_value)


def throttle(callback: EventCallbackType, seconds: float) -> _Throttle:
    """Helper method for throttle callback filter."""
    return _Throttle(callback, seconds)


class _Delta(Filter):
    """Provides ability to pass call difference to the callback."""

    async def __call__(self, new_value):
        """set new value for the callback."""
        old_value = self._value
        if _significantly_changed(old_value, new_value):
            self._value = new_value
            if (difference := _diffence_between(old_value, new_value)) is not None:
                return await self._callback(difference)


def delta(callback: EventCallbackType) -> _Delta:
    """Helper method for delta callback filter."""
    return _Delta(callback)


class _Aggregate(Filter):
    """Provides ability to sum value for some time before sending them
    to the callback."""

    _sum: NumericType
    _last_update: float | None
    _timeout: float

    def __init__(self, callback: EventCallbackType, seconds: float):
        """Initialize Aggregate object."""
        super().__init__(callback)
        self._last_update = time.monotonic()
        self._timeout = seconds
        self._sum = decimal.Decimal()

    async def __call__(self, new_value):
        """Set new value for the callback."""
        current_timestamp = time.monotonic()
        try:
            self._sum += decimal.Decimal(new_value)
        except decimal.InvalidOperation as e:
            raise ValueError(
                "Aggregate filter can only be used with numeric values"
            ) from e

        if current_timestamp - self._last_update >= self._timeout:
            result = await self._callback(self._sum)
            self._last_update = current_timestamp
            self._sum = decimal.Decimal()
            return result


def aggregate(callback: EventCallbackType, seconds: float) -> _Aggregate:
    """Helper method for total callback filter."""
    return _Aggregate(callback, seconds)
