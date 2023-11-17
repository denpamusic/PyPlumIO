"""Contains a boiler power structure decoder."""
from __future__ import annotations

import math
from typing import Final

from pyplumio.helpers.data_types import Float
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_BOILER_POWER: Final = "boiler_power"


class BoilerPowerStructure(StructureDecoder):
    """Represents a boiler power sensor data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        boiler_power = Float.from_bytes(message, offset)
        offset += boiler_power.size

        if math.isnan(boiler_power.value):
            return ensure_dict(data), offset

        return ensure_dict(data, {ATTR_BOILER_POWER: boiler_power.value}), offset
