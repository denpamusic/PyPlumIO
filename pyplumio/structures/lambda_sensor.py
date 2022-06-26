"""Contains lambda structure parser."""
from __future__ import annotations

import math
from typing import Any, Dict, Final, Optional, Tuple

from pyplumio import util
from pyplumio.const import DATA_LAMBDA_SENSOR

LAMBDA_LEVEL: Final = "lambda_level"
LAMBDA_STATUS: Final = "lambda_status"
LAMBDA_TARGET: Final = "lambda_target"
LAMBDA: Final = (
    LAMBDA_LEVEL,
    LAMBDA_STATUS,
    LAMBDA_TARGET,
)


def from_bytes(
    message: bytearray, offset: int = 0, data: Optional[Dict[str, Any]] = None
) -> Tuple[Dict[str, Any], int]:
    """Parse bytes and return message data and offset."""
    if data is None:
        data = {}

    lambda_sensor: Dict[str, Any] = {}
    if message[offset] != 0xFF:
        lambda_sensor[LAMBDA_STATUS] = message[offset]
        lambda_sensor[LAMBDA_TARGET] = message[offset + 1]
        lambda_level = util.unpack_ushort(message[offset + 2 : offset + 4])
        lambda_sensor[LAMBDA_LEVEL] = None if math.isnan(lambda_level) else lambda_level
        offset += 3

    offset += 1
    data[DATA_LAMBDA_SENSOR] = lambda_sensor

    return data, offset
