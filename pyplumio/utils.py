"""Contains various utility methods."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
from functools import reduce, wraps
from typing import Annotated, Final, ParamSpec, TypeAlias, TypeVar

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


SingleByte: TypeAlias = Annotated[int, "Single byte integer between 0 and 255"]

BITS_PER_BYTE: Final = 8


def join_bits(bits: Sequence[bool]) -> SingleByte:
    """Join eight bits into a single byte."""
    if len(bits) > BITS_PER_BYTE:
        raise ValueError("The number of bits must not exceed 8.")

    return reduce(lambda byte, bit: (byte << 1) | int(bit), bits, 0)


MAX_BYTE: Final = 255


def split_byte(byte: SingleByte) -> list[bool]:
    """Split single byte into an eight bits."""
    if byte < 0 or byte > MAX_BYTE:
        raise ValueError("Byte value must be between 0 and 255.")

    if byte == 0:
        return [False, False, False, False, False, False, False, False]

    if byte == MAX_BYTE:
        return [True, True, True, True, True, True, True, True]

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
