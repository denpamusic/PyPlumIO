"""Contains temperatures structure parser."""

import math

from pyplumio import util
from pyplumio.constants import TEMP_NAMES


def from_bytes(message: bytearray, offset: int = 0) -> (dict, int):
    """Parses frame message into usable data.

    Keyword arguments:
    message -- ecoNET message
    offset -- current data offset
    """
    data = {}
    temp_number = message[offset]
    offset += 1
    for _ in range(temp_number):
        index = message[offset]
        temp = util.unpack_float(message[offset + 1 : offset + 5])[0]

        if (not math.isnan(temp)) and 0 <= index < len(TEMP_NAMES):
            # Temperature exists and index is in the correct range.
            data[TEMP_NAMES[index]] = temp

        offset += 5

    return data, offset
