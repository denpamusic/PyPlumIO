"""Contains outputs structure parser."""

import math
from typing import Any, Dict, Final, Tuple

from pyplumio import util

OUTPUTS: Final = (
    "fan",
    "feeder",
    "heating_pump",
    "water_heater_pump",
    "ciculation_pump",
    "lighter",
    "alarm",
    "outer_boiler",
    "fan2_exhaust",
    "feeder2",
    "outer_feeder",
    "solar_pump",
    "fireplace_pump",
    "gcz_contact",
    "blow_fan1",
    "blow_fan2",
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

    outputs = util.unpack_ushort(message[offset : offset + 4])
    for index, output in enumerate(OUTPUTS):
        data[output] = bool(outputs & int(math.pow(2, index)))

    offset += 4

    return data, offset
