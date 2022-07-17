"""Contains type aliases."""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Literal, MutableMapping, Tuple, Union

Numeric = Union[int, float]
ParameterTuple = Tuple[int, int, int]
ParameterValue = Union[Literal["off"], Literal["on"], int, float, bool]
ValueCallback = Callable[[Any], Awaitable[Any]]
AsyncCallback = Callable[[], Awaitable[Any]]
DeviceData = MutableMapping[str, Any]
Versions = MutableMapping[int, int]
Parameters = MutableMapping[str, ParameterTuple]
