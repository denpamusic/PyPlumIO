"""Contains a timeout decorator."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import TypeVar

from typing_extensions import ParamSpec

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

        return wrapper

    return decorator


__all__ = ["timeout"]
