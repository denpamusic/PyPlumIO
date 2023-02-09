"""Contains type aliases."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Literal, Union

NumericType = Union[int, float]
ParameterDataType = tuple[int, int, int]
ParameterValueType = Union[NumericType, bool, Literal["off"], Literal["on"]]
EventDataType = dict[Union[str, int], Any]
EventCallbackType = Callable[[Any], Awaitable[Any]]
VersionsInfoType = dict[int, int]
BytesType = Union[bytes, bytearray]
MessageType = bytearray
