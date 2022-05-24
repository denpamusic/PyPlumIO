"""Contains temperatures structure parser."""

import math
from typing import Any, Dict, Final, Tuple

from pyplumio import util

TEMPERATURES: Final = (
    "heating_temp",
    "feeder_temp",
    "water_heater_temp",
    "outside_temp",
    "back_temp",
    "exhaust_temp",
    "optical_temp",
    "upper_buffer_temp",
    "lower_buffer_temp",
    "upper_solar_temp",
    "lower_solar_temp",
    "fireplace_temp",
    "total_gain",
    "hydraulic_coupler_temp",
    "exchanger_temp",
    "air_in_temp",
    "air_out_temp",
)


def from_bytes(
    message: bytearray, offset: int = 0, data: Dict[str, Any] = None
) -> Tuple[Dict[str, Any], int]:
    """Parses frame message into usable data.

    Keyword arguments:
        message -- message bytes
        offset -- current data offset
    """
    if data is None:
        data = {}

    temp_number = message[offset]
    offset += 1
    for _ in range(temp_number):
        index = message[offset]
        temp = util.unpack_float(message[offset + 1 : offset + 5])[0]

        if (not math.isnan(temp)) and 0 <= index < len(TEMPERATURES):
            # Temperature exists and index is in the correct range.
            data[TEMPERATURES[index]] = temp

        offset += 5

    return data, offset
