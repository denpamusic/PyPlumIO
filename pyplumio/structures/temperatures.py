"""Contains temperatures structure decoder."""
from __future__ import annotations

import math
from typing import Final, Optional, Tuple

from pyplumio import util
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

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
TEMPERATURES: Tuple[str, ...] = (
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
    """Represents temperatures data structures."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        data = ensure_device_data(data)
        temp_count = message[offset]
        offset += 1
        for _ in range(temp_count):
            index = message[offset]
            temp = util.unpack_float(message[offset + 1 : offset + 5])[0]

            if (not math.isnan(temp)) and 0 <= index < len(TEMPERATURES):
                # Temperature exists and index is in the correct range.
                data[TEMPERATURES[index]] = temp

            offset += 5

        return data, offset
