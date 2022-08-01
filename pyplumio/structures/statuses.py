"""Contains outputs structure decoder."""
from __future__ import annotations

from typing import Final, Optional, Tuple

from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, make_device_data

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


class StatusesStructure(StructureDecoder):
    """Represents statuses data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        data = make_device_data(data)
        for index, status in enumerate(STATUSES):
            data[status] = message[offset + index]

        return data, offset + 4
