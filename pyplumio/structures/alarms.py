"""Contains alarms structure decoder."""
from __future__ import annotations

from typing import Optional, Tuple

from pyplumio.const import ATTR_ALARMS
from pyplumio.helpers.typing import DeviceDataType


def from_bytes(
    message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
) -> Tuple[DeviceDataType, int]:
    """Decode bytes and return message data and offset."""
    if data is None:
        data = {}

    alarms = []
    alarms_number = message[offset]
    for i in range(alarms_number):
        alarms.append(message[offset + i])

    offset += alarms_number + 1
    data[ATTR_ALARMS] = alarms

    return data, offset
