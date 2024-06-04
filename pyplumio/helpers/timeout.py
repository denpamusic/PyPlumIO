"""Contains a timeout decorator."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Coroutine
from functools import wraps
import logging
from typing import Any, TypeVar

from typing_extensions import ParamSpec

T = TypeVar("T")
P = ParamSpec("P")

_LOGGER = logging.getLogger(__name__)


def timeout(
    seconds: int,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Coroutine[Any, Any, T]]]:
    """Decorate a timeout for the awaitable."""

    def decorator(
        func: Callable[P, Awaitable[T]],
    ) -> Callable[P, Coroutine[Any, Any, T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)

        return wrapper

    return decorator
