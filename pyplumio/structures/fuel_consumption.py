"""Contains fuel consumption structure decoder."""
from __future__ import annotations

import math
from typing import Final

from pyplumio import util
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_FUEL_CONSUMPTION: Final = "fuel_consumption"


class FuelConsumptionStructure(StructureDecoder):
    """Represents a fuel consumption sensor data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        fuel_consumption = util.unpack_float(message[offset : offset + 4])[0]
        offset += 4
        if not math.isnan(fuel_consumption):
            return (
                ensure_device_data(data, {ATTR_FUEL_CONSUMPTION: fuel_consumption}),
                offset,
            )

        return ensure_device_data(data), offset
