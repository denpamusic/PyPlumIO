"""Contains lambda structure decoder."""
from __future__ import annotations

import math
from typing import Final, Optional, Tuple

from pyplumio import util
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder

ATTR_FAN_POWER: Final = "fan_power"


class FanPowerStructure(StructureDecoder):
    """Represents fan power sensor data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        fan_power = util.unpack_float(message[offset : offset + 4])[0]
        if not math.isnan(fan_power):
            data[ATTR_FAN_POWER] = fan_power

        return data, offset + 4
