"""Contains a fuel level structure decoder."""
from __future__ import annotations

from typing import Final

from pyplumio.const import BYTE_UNDEFINED
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_FUEL_LEVEL: Final = "fuel_level"

FUEL_LEVEL_SIZE: Final = 1


class FuelLevelStructure(StructureDecoder):
    """Represents a fuel level sensor data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        if message[offset] == BYTE_UNDEFINED:
            return ensure_dict(data), offset + FUEL_LEVEL_SIZE

        return (
            ensure_dict(data, {ATTR_FUEL_LEVEL: message[offset]}),
            offset + FUEL_LEVEL_SIZE,
        )
