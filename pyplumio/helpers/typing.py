"""Contains type aliases."""
from __future__ import annotations

from typing import Literal, Protocol, Union

ParameterValueType = Union[int, float, bool, Literal["off"], Literal["on"]]


class SupportsSubtraction(Protocol):
    """Supports subtraction operation."""

    def __sub__(self, other):
        """Subtract a value."""
