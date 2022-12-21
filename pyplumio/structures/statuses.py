"""Contains outputs structure decoder."""
from __future__ import annotations

from typing import Final, Optional, Tuple

from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_HEATING_TARGET: Final = "heating_target"
ATTR_HEATING_STATUS: Final = "heating_status"
ATTR_WATER_HEATER_TARGET: Final = "water_heater_target"
ATTR_WATER_HEATER_STATUS: Final = "water_heater_status"
STATUSES: Tuple[str, ...] = (
    ATTR_HEATING_TARGET,
    ATTR_HEATING_STATUS,
    ATTR_WATER_HEATER_TARGET,
    ATTR_WATER_HEATER_STATUS,
)


class StatusesStructure(StructureDecoder):
    """Represents statuses data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        data = ensure_device_data(data)
        for index, status in enumerate(STATUSES):
            data[status] = message[offset + index]

        return data, offset + 4
