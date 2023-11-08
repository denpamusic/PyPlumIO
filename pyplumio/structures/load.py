"""Contains a boiler load structure decoder."""
from __future__ import annotations

from typing import Final

from pyplumio.const import BYTE_UNDEFINED
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_LOAD: Final = "load"


class LoadStructure(StructureDecoder):
    """Represents a boiler load sensor data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        load = message[offset]
        offset += 1

        if load == BYTE_UNDEFINED:
            return ensure_dict(data), offset

        return (ensure_dict(data, {ATTR_LOAD: message[offset]}), offset)
