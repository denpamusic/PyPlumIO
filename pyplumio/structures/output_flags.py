"""Contains an output flags structure decoder."""

from __future__ import annotations

from typing import Any, Final

from pyplumio.data_types import UnsignedInt
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_HEATING_PUMP_FLAG: Final = "heating_pump_flag"
ATTR_WATER_HEATER_PUMP_FLAG: Final = "water_heater_pump_flag"
ATTR_CIRCULATION_PUMP_FLAG: Final = "circulation_pump_flag"
ATTR_SOLAR_PUMP_FLAG: Final = "solar_pump_flag"


class OutputFlagsStructure(StructureDecoder):
    """Represents an output flags structure."""

    __slots__ = ()

    def decode(
        self, message: bytearray, offset: int = 0, data: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], int]:
        """Decode bytes and return message data and offset."""
        output_flags = UnsignedInt.from_bytes(message, offset)
        return (
            ensure_dict(
                data,
                {
                    ATTR_HEATING_PUMP_FLAG: bool(output_flags.value & 0x04),
                    ATTR_WATER_HEATER_PUMP_FLAG: bool(output_flags.value & 0x08),
                    ATTR_CIRCULATION_PUMP_FLAG: bool(output_flags.value & 0x10),
                    ATTR_SOLAR_PUMP_FLAG: bool(output_flags.value & 0x800),
                },
            ),
            offset + output_flags.size,
        )


__all__ = [
    "ATTR_HEATING_PUMP_FLAG",
    "ATTR_WATER_HEATER_PUMP_FLAG",
    "ATTR_CIRCULATION_PUMP_FLAG",
    "ATTR_SOLAR_PUMP_FLAG",
    "OutputFlagsStructure",
]
