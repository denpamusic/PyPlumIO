"""Contains a boiler load structure decoder."""

from __future__ import annotations

from typing import Any, Final

from pyplumio.const import BYTE_UNDEFINED
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_BOILER_LOAD: Final = "boiler_load"


class BoilerLoadStructure(StructureDecoder):
    """Represents a boiler load sensor data structure."""

    __slots__ = ()

    def decode(
        self, message: bytearray, offset: int = 0, data: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], int]:
        """Decode bytes and return message data and offset."""
        boiler_load = message[offset]
        offset += 1

        if boiler_load == BYTE_UNDEFINED:
            return ensure_dict(data), offset

        return (ensure_dict(data, {ATTR_BOILER_LOAD: boiler_load}), offset)
