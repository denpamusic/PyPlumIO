"""Contains lambda structure decoder."""
from __future__ import annotations

from typing import Final, Optional, Tuple

from pyplumio.const import BYTE_UNDEFINED
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_FUEL_LEVEL: Final = "fuel_level"


class FuelLevelStructure(StructureDecoder):
    """Represents fuel level sensor data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        if message[offset] == BYTE_UNDEFINED:
            return ensure_device_data(data), offset + 1

        return ensure_device_data(data, {ATTR_FUEL_LEVEL: message[offset]}), offset + 1
