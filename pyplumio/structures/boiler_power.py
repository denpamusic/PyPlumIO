"""Contains a boiler power structure decoder."""
from __future__ import annotations

import math
from typing import Any, Final

from pyplumio.helpers.data_types import Float
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_BOILER_POWER: Final = "boiler_power"


class BoilerPowerStructure(StructureDecoder):
    """Represents a boiler power sensor data structure."""

    __slots__ = ()

    def decode(
        self, message: bytearray, offset: int = 0, data: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], int]:
        """Decode bytes and return message data and offset."""
        boiler_power = Float.from_bytes(message, offset)
        offset += boiler_power.size

        if math.isnan(boiler_power.value):
            return ensure_dict(data), offset

        return ensure_dict(data, {ATTR_BOILER_POWER: boiler_power.value}), offset
