"""Contains lambda structure parser."""

import math

from pyplumio import util


def from_bytes(message: bytearray, offset: int = 0) -> (dict, int):
    """Parses frame message into usable data.

    Keyword arguments:
    message -- ecoNET message
    offset -- current data offset
    """
    data = {}
    if message[offset] == 0xFF:
        offset += 1
        return data, offset

    data["lambdaStatus"] = message[offset]
    data["lambdaSet"] = message[offset + 1]
    lambda_level = util.unpack_ushort(message[offset + 2 : offset + 4])
    if math.isnan(lambda_level):
        lambda_level = None

    data["lambdaLevel"] = lambda_level
    offset += 4

    return data, offset
