"""Contains lambda structure decoder."""
from __future__ import annotations

import math
from typing import Final, Optional, Tuple

from pyplumio import util
from pyplumio.const import ATTR_LAMBDA_SENSOR, BYTE_UNDEFINED
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_LAMBDA_LEVEL: Final = "lambda_level"
ATTR_LAMBDA_STATUS: Final = "lambda_status"
ATTR_LAMBDA_TARGET: Final = "lambda_target"


class LambaSensorStructure(StructureDecoder):
    """Represents lambda sensor data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        lambda_sensor: DeviceDataType = {}
        if message[offset] != BYTE_UNDEFINED:
            lambda_sensor[ATTR_LAMBDA_STATUS] = message[offset]
            lambda_sensor[ATTR_LAMBDA_TARGET] = message[offset + 1]
            lambda_level = util.unpack_ushort(message[offset + 2 : offset + 4])
            lambda_sensor[ATTR_LAMBDA_LEVEL] = (
                None if math.isnan(lambda_level) else lambda_level
            )
            offset += 3

        return ensure_device_data(data, {ATTR_LAMBDA_SENSOR: lambda_sensor}), offset + 1
