"""Contains a boiler power structure decoder."""
from __future__ import annotations

import math
from typing import Final

from pyplumio.helpers.data_types import unpack_float
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_POWER: Final = "power"

POWER_SIZE: Final = 4


class PowerStructure(StructureDecoder):
    """Represents a boiler power sensor data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        power = unpack_float(message[offset : offset + 4])[0]
        if not math.isnan(power):
            return ensure_device_data(data, {ATTR_POWER: power}), offset + POWER_SIZE

        return ensure_device_data(data), offset + POWER_SIZE
