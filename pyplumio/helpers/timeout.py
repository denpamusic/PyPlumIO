"""Contains timeout decorator."""
from __future__ import annotations

import asyncio
import logging

_LOGGER = logging.getLogger(__name__)


def timeout(seconds: int, raise_exception: bool = True):
    """Decorator to add a timeout to the awaitable. Returns None if
    raise_exception parameter is set to false."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                if raise_exception:
                    raise

                _LOGGER.warning(
                    "Timeout error: function timed out after %i second. %s%s",
                    seconds,
                    func.__name__,
                    repr(args),
                )
                return None

        return wrapper

    return decorator
