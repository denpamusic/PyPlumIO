"""Contains lambda structure decoder."""
from __future__ import annotations

from typing import Optional, Tuple

from pyplumio import util
from pyplumio.const import ATTR_FUEL_LEVEL
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder


class FuelLevelStructure(StructureDecoder):
    """Represents fuel level sensor data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        if util.check_value(message[offset]):
            data[ATTR_FUEL_LEVEL] = message[offset]

        return data, offset + 1
