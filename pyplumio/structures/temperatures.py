"""Contains a temperatures structure decoder."""
from __future__ import annotations

import math
from typing import Final

from pyplumio.helpers.data_types import Float
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_HEATING_TEMP: Final = "heating_temp"
ATTR_FEEDER_TEMP: Final = "feeder_temp"
ATTR_WATER_HEATER_TEMP: Final = "water_heater_temp"
ATTR_OUTSIDE_TEMP: Final = "outside_temp"
ATTR_RETURN_TEMP: Final = "return_temp"
ATTR_EXHAUST_TEMP: Final = "exhaust_temp"
ATTR_OPTICAL_TEMP: Final = "optical_temp"
ATTR_UPPER_BUFFER_TEMP: Final = "upper_buffer_temp"
ATTR_LOWER_BUFFER_TEMP: Final = "lower_buffer_temp"
ATTR_UPPER_SOLAR_TEMP: Final = "upper_solar_temp"
ATTR_LOWER_SOLAR_TEMP: Final = "lower_solar_temp"
ATTR_FIREPLACE_TEMP: Final = "fireplace_temp"
ATTR_TOTAL_GAIN: Final = "total_gain"
ATTR_HYDRAULIC_COUPLER_TEMP: Final = "hydraulic_coupler_temp"
ATTR_EXCHANGER_TEMP: Final = "exchanger_temp"
ATTR_AIR_IN_TEMP: Final = "air_in_temp"
ATTR_AIR_OUT_TEMP: Final = "air_out_temp"

TEMPERATURES: tuple[str, ...] = (
    ATTR_HEATING_TEMP,
    ATTR_FEEDER_TEMP,
    ATTR_WATER_HEATER_TEMP,
    ATTR_OUTSIDE_TEMP,
    ATTR_RETURN_TEMP,
    ATTR_EXHAUST_TEMP,
    ATTR_OPTICAL_TEMP,
    ATTR_UPPER_BUFFER_TEMP,
    ATTR_LOWER_BUFFER_TEMP,
    ATTR_UPPER_SOLAR_TEMP,
    ATTR_LOWER_SOLAR_TEMP,
    ATTR_FIREPLACE_TEMP,
    ATTR_TOTAL_GAIN,
    ATTR_HYDRAULIC_COUPLER_TEMP,
    ATTR_EXCHANGER_TEMP,
    ATTR_AIR_IN_TEMP,
    ATTR_AIR_OUT_TEMP,
)


class TemperaturesStructure(StructureDecoder):
    """Represents a temperatures data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        data = ensure_dict(data)
        temperatures = message[offset]
        offset += 1
        for _ in range(temperatures):
            index = message[offset]
            offset += 1
            temp = Float.from_bytes(message, offset)
            offset += temp.size
            if (not math.isnan(temp.value)) and 0 <= index < len(TEMPERATURES):
                # Temperature exists and index is in the correct range.
                data[TEMPERATURES[index]] = temp.value

        return data, offset
