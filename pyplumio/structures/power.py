"""Contains lambda structure decoder."""
from __future__ import annotations

import math
from typing import Final, Optional, Tuple

from pyplumio import util
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_POWER: Final = "power"


class PowerStructure(StructureDecoder):
    """Represents ecoMAX power sensor data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        power = util.unpack_float(message[offset : offset + 4])[0]
        offset += 4
        if not math.isnan(power):
            return ensure_device_data(data, {ATTR_POWER: power}), offset

        return ensure_device_data(data), offset
