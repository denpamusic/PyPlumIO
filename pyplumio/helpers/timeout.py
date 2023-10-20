"""Contains a timeout decorator."""
from __future__ import annotations

import asyncio
from functools import wraps
import logging

_LOGGER = logging.getLogger(__name__)


def timeout(seconds: int, raise_exception: bool = True):
    """Decorator to add a timeout to the awaitable.

    Return None on exception if raise_exception parameter is set to false.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
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
