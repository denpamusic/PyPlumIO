"""Contains type aliases."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Literal, Protocol, Union

ParameterValueType = Union[int, float, bool, Literal["off"], Literal["on"]]
EventDataType = dict[Union[str, int], Any]
EventCallbackType = Callable[[Any], Awaitable[Any]]


class SupportsSubtraction(Protocol):
    """Supports subtraction operation."""

    def __sub__(self, other):
        """Subtract a value."""
