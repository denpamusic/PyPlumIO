"""Contains fuel consumption structure decoder."""

from __future__ import annotations

import math
from typing import Any, Final

from pyplumio.helpers.data_types import Float
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_FUEL_CONSUMPTION: Final = "fuel_consumption"


class FuelConsumptionStructure(StructureDecoder):
    """Represents a fuel consumption sensor data structure."""

    __slots__ = ()

    def decode(
        self, message: bytearray, offset: int = 0, data: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], int]:
        """Decode bytes and return message data and offset."""
        fuel_consumption = Float.from_bytes(message, offset)
        offset += fuel_consumption.size

        if math.isnan(fuel_consumption.value):
            return ensure_dict(data), offset

        return (
            ensure_dict(data, {ATTR_FUEL_CONSUMPTION: fuel_consumption.value}),
            offset,
        )
