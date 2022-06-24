"""Contains custom typing."""

from collections.abc import Awaitable, Callable
from typing import Any, Tuple, Union

ParameterTuple = Tuple[str, int, int, int]
Numeric = Union[int, float]
AsyncCallback = Callable[[Any], Awaitable[Any]]
