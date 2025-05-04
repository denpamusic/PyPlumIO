"""Contains a simple async cache for caching results of async functions."""

from collections.abc import Awaitable
from functools import wraps
from typing import Any, Callable, TypeVar, cast

from typing_extensions import ParamSpec, TypeAlias

T = TypeVar("T")
P = ParamSpec("P")
_CallableT: TypeAlias = Callable[..., Awaitable[Any]]


class AsyncCache:
    """A simple cache for asynchronous functions."""

    __slots__ = ("cache",)

    cache: dict[str, Any]

    def __init__(self) -> None:
        """Initialize the cache."""
        self.cache = {}

    async def get(self, key: str, coro: _CallableT) -> Any:
        """Get a value from the cache or compute and store it."""
        if key not in self.cache:
            self.cache[key] = await coro()

        return self.cache[key]


# Create a global cache instance
async_cache = AsyncCache()


def acache(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
    """Cache the result of an async function."""

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        func_name = f"{func.__module__}.{func.__qualname__}"
        key = f"{func_name}:{args}:{kwargs}"
        return cast(T, await async_cache.get(key, lambda: func(*args, **kwargs)))

    return wrapper


__all__ = ["acache", "async_cache"]
