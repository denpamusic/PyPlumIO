"""Contains fuel consumption structure decoder."""
from __future__ import annotations

import math
from typing import Final

from pyplumio.helpers.data_types import unpack_float
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_FUEL_CONSUMPTION: Final = "fuel_consumption"

FUEL_CONSUMPTION_SIZE: Final = 4


class FuelConsumptionStructure(StructureDecoder):
    """Represents a fuel consumption sensor data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        fuel_consumption = unpack_float(message[offset : offset + 4])[0]
        if not math.isnan(fuel_consumption):
            return (
                ensure_dict(data, {ATTR_FUEL_CONSUMPTION: fuel_consumption}),
                offset + FUEL_CONSUMPTION_SIZE,
            )

        return ensure_dict(data), offset + FUEL_CONSUMPTION_SIZE
