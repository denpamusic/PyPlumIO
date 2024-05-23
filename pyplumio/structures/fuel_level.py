"""Contains a fuel level structure decoder."""

from __future__ import annotations

from typing import Any, Final

from pyplumio.const import BYTE_UNDEFINED
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_FUEL_LEVEL: Final = "fuel_level"

FUEL_LEVEL_OFFSET: Final = 101


class FuelLevelStructure(StructureDecoder):
    """Represents a fuel level sensor data structure."""

    __slots__ = ()

    def decode(
        self, message: bytearray, offset: int = 0, data: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], int]:
        """Decode bytes and return message data and offset."""
        fuel_level = message[offset]
        offset += 1

        if fuel_level == BYTE_UNDEFINED:
            return ensure_dict(data), offset

        if fuel_level >= FUEL_LEVEL_OFFSET:
            # Observed on at least ecoMAX 860P6-O.
            # See: https://github.com/denpamusic/PyPlumIO/issues/19
            fuel_level -= FUEL_LEVEL_OFFSET

        return (ensure_dict(data, {ATTR_FUEL_LEVEL: fuel_level}), offset)
