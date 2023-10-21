"""Contains a fan power structure decoder."""
from __future__ import annotations

import math
from typing import Final

from pyplumio.helpers.data_types import unpack_float
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_FAN_POWER: Final = "fan_power"

FAN_POWER_SIZE: Final = 4


class FanPowerStructure(StructureDecoder):
    """Represents a fan power sensor data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        fan_power = unpack_float(message[offset : offset + FAN_POWER_SIZE])[0]
        if not math.isnan(fan_power):
            data = ensure_dict(data, {ATTR_FAN_POWER: fan_power})

        return data, offset + FAN_POWER_SIZE
