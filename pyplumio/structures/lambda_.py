"""Contains lambda structure parser."""

import math
from typing import Any, Dict, Final, Tuple

from pyplumio import util

LAMBDA_LEVEL: Final = "lambda_level"
LAMBDA_STATUS: Final = "lambda_status"
LAMBDA_TARGET: Final = "lambda_target"
LAMBDA: Final = (
    LAMBDA_LEVEL,
    LAMBDA_STATUS,
    LAMBDA_TARGET,
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

    if message[offset] == 0xFF:
        offset += 1
        return data, offset

    data[LAMBDA_STATUS] = message[offset]
    data[LAMBDA_TARGET] = message[offset + 1]
    lambda_level = util.unpack_ushort(message[offset + 2 : offset + 4])
    data[LAMBDA_LEVEL] = None if math.isnan(lambda_level) else lambda_level
    offset += 4

    return data, offset
