"""Contains output flags structure decoder."""
from __future__ import annotations

from typing import Final, Optional, Tuple

from pyplumio import util
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import Structure

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


class OutputFlagsStructure(Structure):
    """Represents output flags structure."""

    def encode(self, data: DeviceDataType) -> bytearray:
        """Encode device data to bytearray message."""
        return bytearray()

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        if data is None:
            data = {}

        output_flags = util.unpack_ushort(message[offset : offset + 4])
        data[HEATING_PUMP_FLAG] = bool(output_flags & 0x04)
        data[WATER_HEATER_PUMP_FLAG] = bool(output_flags & 0x08)
        data[CIRCULATION_PUMP_FLAG] = bool(output_flags & 0x10)
        data[SOLAR_PUMP_FLAG] = bool(output_flags & 0x800)
        offset += 4

        return data, offset
