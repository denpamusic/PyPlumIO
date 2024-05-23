"""Contains type aliases."""

from __future__ import annotations

from typing import Literal, Protocol, Union, runtime_checkable

ParameterValueType = Union[int, float, bool, Literal["off"], Literal["on"]]


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
