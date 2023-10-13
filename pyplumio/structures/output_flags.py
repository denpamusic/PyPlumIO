"""Contains an output flags structure decoder."""
from __future__ import annotations

from typing import Final

from pyplumio import util
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_HEATING_PUMP_FLAG: Final = "heating_pump_flag"
ATTR_WATER_HEATER_PUMP_FLAG: Final = "water_heater_pump_flag"
ATTR_CIRCULATION_PUMP_FLAG: Final = "circulation_pump_flag"
ATTR_SOLAR_PUMP_FLAG: Final = "solar_pump_flag"

OUTPUT_FLAGS_SIZE: Final = 4


class OutputFlagsStructure(StructureDecoder):
    """Represents an output flags structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        output_flags = util.unpack_ushort(message[offset : offset + OUTPUT_FLAGS_SIZE])
        return (
            ensure_device_data(
                data,
                {
                    ATTR_HEATING_PUMP_FLAG: bool(output_flags & 0x04),
                    ATTR_WATER_HEATER_PUMP_FLAG: bool(output_flags & 0x08),
                    ATTR_CIRCULATION_PUMP_FLAG: bool(output_flags & 0x10),
                    ATTR_SOLAR_PUMP_FLAG: bool(output_flags & 0x800),
                },
            ),
            offset + OUTPUT_FLAGS_SIZE,
        )
