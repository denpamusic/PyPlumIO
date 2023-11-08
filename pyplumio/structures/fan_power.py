"""Contains a fan power structure decoder."""
from __future__ import annotations

import math
from typing import Final

from pyplumio.helpers.data_types import Float
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_FAN_POWER: Final = "fan_power"


class FanPowerStructure(StructureDecoder):
    """Represents a fan power sensor data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        fan_power = Float.from_bytes(message, offset)
        offset += fan_power.size

        if math.isnan(fan_power.value):
            return ensure_dict(data), offset

        return ensure_dict(data, {ATTR_FAN_POWER: fan_power.value}), offset
