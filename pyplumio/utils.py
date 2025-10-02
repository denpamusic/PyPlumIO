"""Contains various utility methods."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
from functools import reduce, wraps
from typing import ParamSpec, TypeVar

KT = TypeVar("KT")  # Key type.
VT = TypeVar("VT")  # Value type.


def ensure_dict(initial: dict[KT, VT] | None, *args: dict[KT, VT]) -> dict[KT, VT]:
    """Create or merge multiple dictionaries."""
    data = initial if initial is not None else {}
    for extra in args:
        data |= extra

    return data


def to_camelcase(text: str, overrides: Mapping[str, str] | None = None) -> str:
    """Convert snake_case to CamelCase."""
    if not overrides:
        return "".join((x.capitalize() or "_") for x in text.split("_"))

    return "".join(
        (x.capitalize() or "_") if x.lower() not in overrides else overrides[x.lower()]
        for x in text.split("_")
    )


def is_divisible(a: float, b: float, precision: int = 6) -> bool:
    """Check if a is divisible by b."""
    scale: int = 10**precision
    b_scaled = round(b * scale)
    if b_scaled == 0:
        raise ValueError("Division by zero is not allowed.")

    a_scaled = round(a * scale)
    return a_scaled % b_scaled == 0


def join_bits(bits: Sequence[int | bool]) -> int:
    """Join eight bits into a single byte."""
    return reduce(lambda bit, byte: (bit << 1) | byte, bits)


def split_byte(byte: int) -> list[bool]:
    """Split single byte into an eight bits."""
    return [bool(byte & (1 << bit)) for bit in reversed(range(8))]


T = TypeVar("T")
P = ParamSpec("P")


def timeout(
    seconds: float,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Decorate a timeout for the awaitable."""

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)

        setattr(wrapper, "_has_timeout_seconds", seconds)
        return wrapper

    return decorator


__all__ = ["ensure_dict", "is_divisible", "to_camelcase", "timeout"]
