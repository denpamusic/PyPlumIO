"""Contains temperatures structure decoder."""
from __future__ import annotations

import math
from typing import Final, Optional, Tuple

from pyplumio import util
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, make_device_data

HEATING_TEMP: Final = "heating_temp"
FEEDER_TEMP: Final = "feeder_temp"
WATER_HEATER_TEMP: Final = "water_heater_temp"
OUTSIDE_TEMP: Final = "outside_temp"
RETURN_TEMP: Final = "return_temp"
EXHAUST_TEMP: Final = "exhaust_temp"
OPTICAL_TEMP: Final = "optical_temp"
UPPER_BUFFER_TEMP: Final = "upper_buffer_temp"
LOWER_BUFFER_TEMP: Final = "lower_buffer_temp"
UPPER_SOLAR_TEMP: Final = "upper_solar_temp"
LOWER_SOLAR_TEMP: Final = "lower_solar_temp"
FIREPLACE_TEMP: Final = "fireplace_temp"
TOTAL_GAIN: Final = "total_gain"
HYDRAULIC_COUPLER_TEMP: Final = "hydraulic_coupler_temp"
EXCHANGER_TEMP: Final = "exchanger_temp"
AIR_IN_TEMP: Final = "air_in_temp"
AIR_OUT_TEMP: Final = "air_out_temp"
TEMPERATURES: Tuple[str, ...] = (
    HEATING_TEMP,
    FEEDER_TEMP,
    WATER_HEATER_TEMP,
    OUTSIDE_TEMP,
    RETURN_TEMP,
    EXHAUST_TEMP,
    OPTICAL_TEMP,
    UPPER_BUFFER_TEMP,
    LOWER_BUFFER_TEMP,
    UPPER_SOLAR_TEMP,
    LOWER_SOLAR_TEMP,
    FIREPLACE_TEMP,
    TOTAL_GAIN,
    HYDRAULIC_COUPLER_TEMP,
    EXCHANGER_TEMP,
    AIR_IN_TEMP,
    AIR_OUT_TEMP,
)


class TemperaturesStructure(StructureDecoder):
    """Represents temperatures data structures."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        temp_number = message[offset]
        offset += 1
        data = make_device_data(data)
        for _ in range(temp_number):
            index = message[offset]
            temp = util.unpack_float(message[offset + 1 : offset + 5])[0]

            if (not math.isnan(temp)) and 0 <= index < len(TEMPERATURES):
                # Temperature exists and index is in the correct range.
                data[TEMPERATURES[index]] = temp

            offset += 5

        return data, offset
