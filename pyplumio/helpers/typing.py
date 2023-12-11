"""Contains type aliases."""
from __future__ import annotations

from typing import Literal, Protocol, TypeVar, Union, runtime_checkable

T = TypeVar("T")

ParameterValueType = Union[int, float, bool, Literal["off"], Literal["on"]]


@runtime_checkable
class Subtractable(Protocol[T]):
    """Supports subtraction operation."""

    __slots__ = ()

    def __sub__(self, other: T) -> T:
        """Subtract a value."""


@runtime_checkable
class Comparable(Protocol):
    """Supports comparison."""

    __slots__ = ()

    def __eq__(self, other) -> bool:
        """Compare a value."""
