"""Contains outputs structure decoder."""
from __future__ import annotations

import math
from typing import Final, Optional, Tuple

from pyplumio import util
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_FAN_OUTPUT: Final = "fan"
ATTR_FEEDER_OUTPUT: Final = "feeder"
ATTR_HEATING_PUMP_OUTPUT: Final = "heating_pump"
ATTR_WATER_HEATER_PUMP_OUTPUT: Final = "water_heater_pump"
ATTR_CIRCULATION_PUMP_OUTPUT: Final = "ciculation_pump"
ATTR_LIGHTER_OUTPUT: Final = "lighter"
ATTR_ALARM_OUTPUT: Final = "alarm"
ATTR_OUTER_BOILER_OUTPUT: Final = "outer_boiler"
ATTR_FAN2_EXHAUST_OUTPUT: Final = "fan2_exhaust"
ATTR_FEEDER2_OUTPUT: Final = "feeder2"
ATTR_OUTER_FEEDER_OUTPUT: Final = "outer_feeder"
ATTR_SOLAR_PUMP_OUTPUT: Final = "solar_pump"
ATTR_FIREPLACE_PUMP_OUTPUT: Final = "fireplace_pump"
ATTR_GCZ_CONTACT: Final = "gcz_contact"
ATTR_BLOW_FAN1_OUTPUT: Final = "blow_fan1"
ATTR_BLOW_FAN2_OUTPUT: Final = "blow_fan2"
OUTPUTS: Tuple[str, ...] = (
    ATTR_FAN_OUTPUT,
    ATTR_FEEDER_OUTPUT,
    ATTR_HEATING_PUMP_OUTPUT,
    ATTR_WATER_HEATER_PUMP_OUTPUT,
    ATTR_CIRCULATION_PUMP_OUTPUT,
    ATTR_LIGHTER_OUTPUT,
    ATTR_ALARM_OUTPUT,
    ATTR_OUTER_BOILER_OUTPUT,
    ATTR_FAN2_EXHAUST_OUTPUT,
    ATTR_FEEDER2_OUTPUT,
    ATTR_OUTER_FEEDER_OUTPUT,
    ATTR_SOLAR_PUMP_OUTPUT,
    ATTR_FIREPLACE_PUMP_OUTPUT,
    ATTR_GCZ_CONTACT,
    ATTR_BLOW_FAN1_OUTPUT,
    ATTR_BLOW_FAN2_OUTPUT,
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
