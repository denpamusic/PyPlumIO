"""Contains a lambda sensor structure decoder."""

from __future__ import annotations

from contextlib import suppress
from typing import Any, Final

from pyplumio.const import BYTE_UNDEFINED, LambdaState
from pyplumio.data_types import UnsignedShort
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_LAMBDA_STATE: Final = "lambda_state"
ATTR_LAMBDA_TARGET: Final = "lambda_target"
ATTR_LAMBDA_LEVEL: Final = "lambda_level"


class LambdaSensorStructure(StructureDecoder):
    """Represents a lambda sensor data structure."""

    __slots__ = ()

    def decode(
        self, message: bytearray, offset: int = 0, data: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], int]:
        """Decode bytes and return message data and offset."""
        lambda_state = message[offset]
        offset += 1
        if lambda_state == BYTE_UNDEFINED:
            return ensure_dict(data), offset

        lambda_target = message[offset]
        offset += 1
        level = UnsignedShort.from_bytes(message, offset)
        offset += level.size
        with suppress(ValueError):
            lambda_state = LambdaState(lambda_state)

        return (
            ensure_dict(
                data,
                {
                    ATTR_LAMBDA_STATE: lambda_state,
                    ATTR_LAMBDA_TARGET: lambda_target,
                    ATTR_LAMBDA_LEVEL: level.value / 10,
                },
            ),
            offset,
        )


__all__ = [
    "ATTR_LAMBDA_STATE",
    "ATTR_LAMBDA_TARGET",
    "ATTR_LAMBDA_LEVEL",
    "LambdaSensorStructure",
]
