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
    seconds: int, raise_exception: bool = True
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Coroutine[Any, Any, T | None]]]:
    """Decorate a timeout for the awaitable.

    Return None on exception if raise_exception parameter is set to false.
    """

    def decorator(
        func: Callable[P, Awaitable[T]],
    ) -> Callable[P, Coroutine[Any, Any, T | None]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | None:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                if raise_exception:
                    raise

                _LOGGER.warning(
                    "Function '%s' timed out after %i seconds",
                    func.__name__,
                    seconds,
                )
                return None

        return wrapper

    return decorator
