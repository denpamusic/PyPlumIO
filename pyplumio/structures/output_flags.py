"""Contains output flags structure decoder."""
from __future__ import annotations

from typing import Final, Optional, Tuple

from pyplumio import util
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, make_device_data

HEATING_PUMP_FLAG: Final = "heating_pump_flag"
WATER_HEATER_PUMP_FLAG: Final = "water_heater_pump_flag"
CIRCULATION_PUMP_FLAG: Final = "circulation_pump_flag"
SOLAR_PUMP_FLAG: Final = "solar_pump_flag"
OUTPUT_FLAGS: Tuple[str, ...] = (
    HEATING_PUMP_FLAG,
    WATER_HEATER_PUMP_FLAG,
    CIRCULATION_PUMP_FLAG,
    SOLAR_PUMP_FLAG,
)


class OutputFlagsStructure(StructureDecoder):
    """Represents output flags structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        output_flags = util.unpack_ushort(message[offset : offset + 4])
        data = make_device_data(
            data,
            {
                HEATING_PUMP_FLAG: bool(output_flags & 0x04),
                WATER_HEATER_PUMP_FLAG: bool(output_flags & 0x08),
                CIRCULATION_PUMP_FLAG: bool(output_flags & 0x10),
                SOLAR_PUMP_FLAG: bool(output_flags & 0x800),
            },
        )
        return data, offset + 4
