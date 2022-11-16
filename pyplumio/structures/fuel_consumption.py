"""Contains lambda structure decoder."""
from __future__ import annotations

import math
from typing import Optional, Tuple

from pyplumio import util
from pyplumio.const import ATTR_FUEL_CONSUMPTION
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder


class FuelConsumptionStructure(StructureDecoder):
    """Represents fuel consumption sensor data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        fuel_consumption = util.unpack_float(message[offset : offset + 4])[0]
        if not math.isnan(fuel_consumption):
            data[ATTR_FUEL_CONSUMPTION] = fuel_consumption

        return data, offset + 4
