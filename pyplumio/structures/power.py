"""Contains a boiler power structure decoder."""
from __future__ import annotations

import math
from typing import Final

from pyplumio.helpers.data_types import Float
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_POWER: Final = "power"


class PowerStructure(StructureDecoder):
    """Represents a boiler power sensor data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        power = Float.from_bytes(message, offset)
        offset += power.size

        if math.isnan(power.value):
            return ensure_dict(data), offset

        return ensure_dict(data, {ATTR_POWER: power.value}), offset
