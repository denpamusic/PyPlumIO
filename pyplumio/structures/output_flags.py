"""Contains output flags structure parser."""
from __future__ import annotations

from typing import Final, List, Optional, Tuple

from pyplumio import util
from pyplumio.helpers.typing import Records

DATA_HEATING_PUMP_FLAG: Final = "heating_pump_flag"
DATA_WATER_HEATER_PUMP_FLAG: Final = "water_heater_pump_flag"
DATA_CIRCULATION_PUMP_FLAG: Final = "circulation_pump_flag"
DATA_SOLAR_PUMP_FLAG: Final = "solar_pump_flag"
OUTPUT_FLAGS: List[str] = [
    DATA_HEATING_PUMP_FLAG,
    DATA_WATER_HEATER_PUMP_FLAG,
    DATA_CIRCULATION_PUMP_FLAG,
    DATA_SOLAR_PUMP_FLAG,
]


def from_bytes(
    message: bytearray, offset: int = 0, data: Optional[Records] = None
) -> Tuple[Records, int]:
    """Parse bytes and return message data and offset."""
    if data is None:
        data = {}

    output_flags = util.unpack_ushort(message[offset : offset + 4])
    data[DATA_HEATING_PUMP_FLAG] = bool(output_flags & 0x04)
    data[DATA_WATER_HEATER_PUMP_FLAG] = bool(output_flags & 0x08)
    data[DATA_CIRCULATION_PUMP_FLAG] = bool(output_flags & 0x10)
    data[DATA_SOLAR_PUMP_FLAG] = bool(output_flags & 0x800)
    offset += 4

    return data, offset
