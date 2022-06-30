"""Contains lambda structure parser."""
from __future__ import annotations

from collections.abc import Sequence
import math
from typing import Final, Optional, Tuple

from pyplumio import util
from pyplumio.const import DATA_LAMBDA_SENSOR
from pyplumio.helpers.typing import Records

LAMBDA_LEVEL: Final = "lambda_level"
LAMBDA_STATUS: Final = "lambda_status"
LAMBDA_TARGET: Final = "lambda_target"
LAMBDA: Sequence[str] = (
    LAMBDA_LEVEL,
    LAMBDA_STATUS,
    LAMBDA_TARGET,
)


def from_bytes(
    message: bytearray, offset: int = 0, data: Optional[Records] = None
) -> Tuple[Records, int]:
    """Parse bytes and return message data and offset."""
    if data is None:
        data = {}

    lambda_sensor: Records = {}
    if message[offset] != 0xFF:
        lambda_sensor[LAMBDA_STATUS] = message[offset]
        lambda_sensor[LAMBDA_TARGET] = message[offset + 1]
        lambda_level = util.unpack_ushort(message[offset + 2 : offset + 4])
        lambda_sensor[LAMBDA_LEVEL] = None if math.isnan(lambda_level) else lambda_level
        offset += 3

    offset += 1
    data[DATA_LAMBDA_SENSOR] = lambda_sensor

    return data, offset
