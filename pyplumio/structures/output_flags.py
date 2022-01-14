"""Contains output flags structure parser."""

from pyplumio import util
from pyplumio.constants import (
    DATA_CIRCULATION_PUMP_FLAG,
    DATA_CO_PUMP_FLAG,
    DATA_CWU_PUMP_FLAG,
    DATA_SOLAR_PUMP_FLAG,
)


def from_bytes(message: bytearray, offset: int = 0, data: dict = None) -> (dict, int):
    """Parses frame message into usable data.

    Keyword arguments:
    message -- ecoNET message
    offset -- current data offset
    """
    if data is None:
        data = {}

    output_flags = util.unpack_ushort(message[offset : offset + 4])
    data[DATA_CO_PUMP_FLAG] = bool(output_flags & 0x004)
    data[DATA_CWU_PUMP_FLAG] = bool(output_flags & 0x008)
    data[DATA_CIRCULATION_PUMP_FLAG] = bool(output_flags & 0x010)
    data[DATA_SOLAR_PUMP_FLAG] = bool(output_flags & 0x800)
    offset += 4

    return data, offset
