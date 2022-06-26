"""Contains custom typing."""

from typing import Any, Awaitable, Callable, Literal, Tuple, Union

Numeric = Union[int, float]
ParameterTuple = Tuple[str, int, int, int]
ParameterValue = Union[Literal["off"], Literal["on"], int, float, bool]
AsyncCallback = Callable[[Any], Awaitable[Any]]