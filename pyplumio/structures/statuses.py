"""Contains outputs structure parser."""
from __future__ import annotations

from typing import Final, Optional, Tuple

from pyplumio.helpers.typing import DeviceDataType

HEATING_TARGET: Final = "heating_target"
HEATING_STATUS: Final = "heating_status"
WATER_HEATER_TARGET: Final = "water_heater_target"
WATER_HEATER_STATUS: Final = "water_heater_status"
STATUSES: Tuple[str, ...] = (
    HEATING_TARGET,
    HEATING_STATUS,
    WATER_HEATER_TARGET,
    WATER_HEATER_STATUS,
)


def from_bytes(
    message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
) -> Tuple[DeviceDataType, int]:
    """Parse bytes and return message data and offset."""
    if data is None:
        data = {}

    for index, status in enumerate(STATUSES):
        data[status] = message[offset + index]

    offset += 4

    return data, offset
