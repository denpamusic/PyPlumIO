"""Contains timeout decorator."""

import asyncio


def timeout(seconds: int, raise_exception=True):
    """Decorator to add a timeout to the awaitable."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                if raise_exception:
                    raise

                return None

        return wrapper

    return decorator
