"""Contains lambda sensor structure decoder."""
from __future__ import annotations

import math
from typing import Final, Optional, Tuple

from pyplumio import util
from pyplumio.const import BYTE_UNDEFINED
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_LAMBDA_STATE: Final = "lambda_state"
ATTR_LAMBDA_TARGET: Final = "lambda_target"
ATTR_LAMBDA_LEVEL: Final = "lambda_level"


class LambaSensorStructure(StructureDecoder):
    """Represents lambda sensor data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        if message[offset] == BYTE_UNDEFINED:
            return ensure_device_data(data), offset + 1

        state = message[offset]
        target = message[offset + 1]
        level = util.unpack_ushort(message[offset + 2 : offset + 4])

        return (
            ensure_device_data(
                data,
                {
                    ATTR_LAMBDA_STATE: state,
                    ATTR_LAMBDA_TARGET: target,
                    ATTR_LAMBDA_LEVEL: None if math.isnan(level) else level,
                },
            ),
            offset + 4,
        )
