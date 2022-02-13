"""Contains output flags structure parser."""

from typing import Any, Dict, Tuple

from pyplumio import util
from pyplumio.constants import (
    DATA_CIRCULATION_PUMP_FLAG,
    DATA_HEATING_PUMP_FLAG,
    DATA_SOLAR_PUMP_FLAG,
    DATA_WATER_HEATER_PUMP_FLAG,
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

    output_flags = util.unpack_ushort(message[offset : offset + 4])
    data[DATA_HEATING_PUMP_FLAG] = bool(output_flags & 0x004)
    data[DATA_WATER_HEATER_PUMP_FLAG] = bool(output_flags & 0x008)
    data[DATA_CIRCULATION_PUMP_FLAG] = bool(output_flags & 0x010)
    data[DATA_SOLAR_PUMP_FLAG] = bool(output_flags & 0x800)
    offset += 4

    return data, offset
