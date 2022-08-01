"""Contains lambda structure decoder."""
from __future__ import annotations

import math
from typing import Final, Optional, Tuple

from pyplumio import util
from pyplumio.const import ATTR_LAMBDA_SENSOR
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, make_device_data

LAMBDA_LEVEL: Final = "lambda_level"
LAMBDA_STATUS: Final = "lambda_status"
LAMBDA_TARGET: Final = "lambda_target"
LAMBDA: Tuple[str, ...] = (
    LAMBDA_LEVEL,
    LAMBDA_STATUS,
    LAMBDA_TARGET,
)


class LambaSensorStructure(StructureDecoder):
    """Represents lambda sensor data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        lambda_sensor: DeviceDataType = {}
        if message[offset] != 0xFF:
            lambda_sensor[LAMBDA_STATUS] = message[offset]
            lambda_sensor[LAMBDA_TARGET] = message[offset + 1]
            lambda_level = util.unpack_ushort(message[offset + 2 : offset + 4])
            lambda_sensor[LAMBDA_LEVEL] = (
                None if math.isnan(lambda_level) else lambda_level
            )
            offset += 3

        return make_device_data(data, {ATTR_LAMBDA_SENSOR: lambda_sensor}), offset + 1
