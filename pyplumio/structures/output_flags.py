"""Contains output flags structure decoder."""
from __future__ import annotations

from typing import Final, Optional, Tuple

from pyplumio import util
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_HEATING_PUMP_FLAG: Final = "heating_pump_flag"
ATTR_WATER_HEATER_PUMP_FLAG: Final = "water_heater_pump_flag"
ATTR_CIRCULATION_PUMP_FLAG: Final = "circulation_pump_flag"
ATTR_SOLAR_PUMP_FLAG: Final = "solar_pump_flag"


class OutputFlagsStructure(StructureDecoder):
    """Represents output flags structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        output_flags = util.unpack_ushort(message[offset : offset + 4])
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
            offset + 4,
        )
