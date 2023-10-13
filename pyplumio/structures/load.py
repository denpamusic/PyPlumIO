"""Contains a boiler load structure decoder."""
from __future__ import annotations

from typing import Final

from pyplumio.const import BYTE_UNDEFINED
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_LOAD: Final = "load"

LOAD_SIZE: Final = 1


class LoadStructure(StructureDecoder):
    """Represents a boiler load sensor data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        if message[offset] == BYTE_UNDEFINED:
            return ensure_device_data(data), offset + LOAD_SIZE

        return (
            ensure_device_data(data, {ATTR_LOAD: message[offset]}),
            offset + LOAD_SIZE,
        )
