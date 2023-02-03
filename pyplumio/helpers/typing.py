"""Contains type aliases."""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Literal, Union

NumericType = Union[int, float]
ParameterDataType = tuple[int, int, int]
ParameterValueType = Union[NumericType, bool, Literal["off"], Literal["on"]]
DeviceDataType = dict[str, Any]
SensorCallbackType = Callable[[Any], Awaitable[Any]]
VersionsInfoType = dict[int, int]
BytesType = Union[bytes, bytearray]
MessageType = bytearray
