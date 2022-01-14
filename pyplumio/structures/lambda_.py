"""Contains lambda structure parser."""

import math

from pyplumio import util
from pyplumio.constants import DATA_LAMBDA_LEVEL, DATA_LAMBDA_STATUS, DATA_LAMBDA_TARGET


def from_bytes(message: bytearray, offset: int = 0, data: dict = None) -> (dict, int):
    """Parses frame message into usable data.

    Keyword arguments:
    message -- ecoNET message
    offset -- current data offset
    """
    if data is None:
        data = {}

    if message[offset] == 0xFF:
        offset += 1
        return data, offset

    data[DATA_LAMBDA_STATUS] = message[offset]
    data[DATA_LAMBDA_TARGET] = message[offset + 1]
    lambda_level = util.unpack_ushort(message[offset + 2 : offset + 4])
    if math.isnan(lambda_level):
        lambda_level = None

    data[DATA_LAMBDA_LEVEL] = lambda_level
    offset += 4

    return data, offset
