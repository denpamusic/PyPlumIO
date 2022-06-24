"""Contains custom typing."""

from typing import Any, Awaitable, Callable, Tuple, Union

ParameterTuple = Tuple[str, int, int, int]
Numeric = Union[int, float]
AsyncCallback = Callable[[Any], Awaitable[Any]]
