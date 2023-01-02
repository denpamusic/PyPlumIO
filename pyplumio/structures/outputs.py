"""Contains outputs structure decoder."""
from __future__ import annotations

import math
from typing import Final, Optional, Tuple

from pyplumio import util
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_FAN: Final = "fan"
ATTR_FEEDER: Final = "feeder"
ATTR_HEATING_PUMP: Final = "heating_pump"
ATTR_WATER_HEATER_PUMP: Final = "water_heater_pump"
ATTR_CIRCULATION_PUMP: Final = "ciculation_pump"
ATTR_LIGHTER: Final = "lighter"
ATTR_ALARM: Final = "alarm"
ATTR_OUTER_BOILER: Final = "outer_boiler"
ATTR_FAN2_EXHAUST: Final = "fan2_exhaust"
ATTR_FEEDER2: Final = "feeder2"
ATTR_OUTER_FEEDER: Final = "outer_feeder"
ATTR_SOLAR_PUMP: Final = "solar_pump"
ATTR_FIREPLACE_PUMP: Final = "fireplace_pump"
ATTR_GCZ_CONTACT: Final = "gcz_contact"
ATTR_BLOW_FAN1: Final = "blow_fan1"
ATTR_BLOW_FAN2: Final = "blow_fan2"
OUTPUTS: Tuple[str, ...] = (
    ATTR_FAN,
    ATTR_FEEDER,
    ATTR_HEATING_PUMP,
    ATTR_WATER_HEATER_PUMP,
    ATTR_CIRCULATION_PUMP,
    ATTR_LIGHTER,
    ATTR_ALARM,
    ATTR_OUTER_BOILER,
    ATTR_FAN2_EXHAUST,
    ATTR_FEEDER2,
    ATTR_OUTER_FEEDER,
    ATTR_SOLAR_PUMP,
    ATTR_FIREPLACE_PUMP,
    ATTR_GCZ_CONTACT,
    ATTR_BLOW_FAN1,
    ATTR_BLOW_FAN2,
)


class OutputsStructure(StructureDecoder):
    """Represent outputs data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        outputs = util.unpack_ushort(message[offset : offset + 4])
        data = ensure_device_data(data)
        for index, output in enumerate(OUTPUTS):
            data[output] = bool(outputs & int(math.pow(2, index)))

        return data, offset + 4
