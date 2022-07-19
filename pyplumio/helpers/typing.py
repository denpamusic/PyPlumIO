"""Contains type aliases."""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, Literal, Tuple, Union

NumericType = Union[int, float]
ParameterDataType = Tuple[int, int, int]
ParameterValueType = Union[NumericType, bool, Literal["off"], Literal["on"]]
DeviceDataType = Dict[str, Any]
SensorCallbackType = Callable[[Any], Awaitable[Any]]
VersionsInfoType = Dict[int, int]
BytesType = Union[bytes, bytearray]
MessageType = bytearray
