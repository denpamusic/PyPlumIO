"""Contains various utility methods."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar


def to_camelcase(text: str, overrides: Mapping[str, str] | None = None) -> str:
    """Convert snake_case to CamelCase."""
    if not overrides:
        return "".join((x.capitalize() or "_") for x in text.split("_"))

    return "".join(
        (x.capitalize() or "_") if x.lower() not in overrides else overrides[x.lower()]
        for x in text.split("_")
    )


KT = TypeVar("KT")  # Key type.
VT = TypeVar("VT")  # Value type.


def ensure_dict(initial: dict[KT, VT] | None, *args: dict[KT, VT]) -> dict[KT, VT]:
    """Create or merge multiple dictionaries."""
    data = initial if initial is not None else {}
    for extra in args:
        data |= extra

    return data


def is_divisible(a: float, b: float, precision: int = 6) -> bool:
    """Check if a is divisible by b."""
    scale: int = 10**precision
    b_scaled = round(b * scale)
    if b_scaled == 0:
        raise ValueError("Division by zero is not allowed.")

    a_scaled = round(a * scale)
    return a_scaled % b_scaled == 0
