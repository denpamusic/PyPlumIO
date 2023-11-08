"""Contains a lambda sensor structure decoder."""
from __future__ import annotations

import math
from typing import Final

from pyplumio.const import BYTE_UNDEFINED
from pyplumio.helpers.data_types import UnsignedShort
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_LAMBDA_STATE: Final = "lambda_state"
ATTR_LAMBDA_TARGET: Final = "lambda_target"
ATTR_LAMBDA_LEVEL: Final = "lambda_level"


class LambdaSensorStructure(StructureDecoder):
    """Represents a lambda sensor data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        lambda_state = message[offset]
        offset += 1
        if lambda_state == BYTE_UNDEFINED:
            return ensure_dict(data), offset

        lambda_target = message[offset]
        offset += 1
        level = UnsignedShort.from_bytes(message, offset)
        offset += level.size
        return (
            ensure_dict(
                data,
                {
                    ATTR_LAMBDA_STATE: lambda_state,
                    ATTR_LAMBDA_TARGET: lambda_target,
                    ATTR_LAMBDA_LEVEL: None
                    if math.isnan(level.value)
                    else (level.value / 10),
                },
            ),
            offset,
        )
