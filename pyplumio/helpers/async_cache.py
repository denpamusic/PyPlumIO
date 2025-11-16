"""Contains a simple async cache for caching results of async functions."""

from collections.abc import Awaitable, Callable, Coroutine
from functools import wraps
from types import MappingProxyType
from typing import Any, ParamSpec, TypeVar, cast

T = TypeVar("T")
P = ParamSpec("P")


class AsyncCache:
    """A simple cache for asynchronous functions."""

    __slots__ = ("_cache",)

    _cache: dict[str, Any]

    def __init__(self) -> None:
        """Initialize the cache."""
        self._cache = {}

    async def get(self, key: str, coro: Callable[..., Awaitable[Any]]) -> Any:
        """Get a value from the cache or compute and store it."""
        if key not in self.cache:
            self._cache[key] = await coro()

        return self._cache[key]

    @property
    def cache(self) -> MappingProxyType[str, Any]:
        """Return the internal cache dictionary."""
        return MappingProxyType(self._cache)


# Create a global cache instance
async_cache = AsyncCache()


def acache(func: Callable[P, Awaitable[T]]) -> Callable[P, Coroutine[Any, Any, T]]:
    """Cache the result of an async function."""

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        func_name = f"{func.__module__}.{func.__qualname__}"
        key = f"{func_name}:{args}:{kwargs}"
        return cast(T, await async_cache.get(key, lambda: func(*args, **kwargs)))

    return wrapper


__all__ = ["acache", "async_cache"]
