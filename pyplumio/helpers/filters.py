"""Contains callback filters."""
from __future__ import annotations

from abc import ABC, abstractmethod
import time
from typing import Any, Optional

from pyplumio.helpers.parameter import Parameter
from pyplumio.helpers.typing import ValueCallback


def _significantly_changed(old_value, new_value) -> bool:
    """Check if value is significantly changed."""
    if old_value is None or (isinstance(old_value, Parameter) and old_value.changed):
        return True

    if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
        return round(old_value, 1) != round(new_value, 1)

    return old_value != new_value


class Filter(ABC):
    """Represents base for value callback modifiers."""

    _callback: Any
    _value: Any

    def __init__(self, callback: ValueCallback):
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


def on_change(callback: ValueCallback) -> _OnChange:
    """Helper for change callback filter."""
    return _OnChange(callback)


class _Debounce(Filter):
    """Provides debounce functionality to the callback."""

    _calls: int = 0
    _min_calls: int = 3

    def __init__(self, callback: ValueCallback, min_calls: int):
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


def debounce(callback: ValueCallback, min_calls) -> _Debounce:
    """Helper method for debounce callback filter."""
    return _Debounce(callback, min_calls)


class _Throttle(Filter):
    """Provides throttle functionality to the callback."""

    _last_called: Optional[float]
    _timeout: float

    def __init__(self, callback: ValueCallback, seconds: float):
        """Initialize Debounce object."""
        super().__init__(callback)
        self._last_called = None
        self._timeout = seconds

    async def __call__(self, new_value):
        """Set new value for the callback."""
        current_timestamp = time.time()
        if (
            self._last_called is None
            or (current_timestamp - self._last_called) >= self._timeout
        ):
            self._last_called = current_timestamp
            return await self._callback(new_value)


def throttle(callback: ValueCallback, seconds: float) -> _Throttle:
    """Helper method for throttle callback filter."""
    return _Throttle(callback, seconds)
