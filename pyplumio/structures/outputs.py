"""Contains outputs structure parser."""
from __future__ import annotations

import math
from typing import Final, List, Optional, Tuple

from pyplumio import util
from pyplumio.helpers.typing import Records

FAN_OUTPUT: Final = "fan"
FEEDER_OUTPUT: Final = "feeder"
HEATING_PUMP_OUTPUT: Final = "heating_pump"
WATER_HEATER_PUMP_OUTPUT: Final = "water_heater_pump"
CIRCULATION_PUMP_OUTPUT: Final = "ciculation_pump"
LIGHTER_OUTPUT: Final = "lighter"
ALARM_OUTPUT: Final = "alarm"
OUTER_BOILER_OUTPUT: Final = "outer_boiler"
FAN2_EXHAUST_OUTPUT: Final = "fan2_exhaust"
FEEDER2_OUTPUT: Final = "feeder2"
OUTER_FEEDER_OUTPUT: Final = "outer_feeder"
SOLAR_PUMP_OUTPUT: Final = "solar_pump"
FIREPLACE_PUMP_OUTPUT: Final = "fireplace_pump"
GCZ_CONTACT: Final = "gcz_contact"
BLOW_FAN1_OUTPUT: Final = "blow_fan1"
BLOW_FAN2_OUTPUT: Final = "blow_fan2"
OUTPUTS: List[str] = [
    FAN_OUTPUT,
    FEEDER_OUTPUT,
    HEATING_PUMP_OUTPUT,
    WATER_HEATER_PUMP_OUTPUT,
    CIRCULATION_PUMP_OUTPUT,
    LIGHTER_OUTPUT,
    ALARM_OUTPUT,
    OUTER_BOILER_OUTPUT,
    FAN2_EXHAUST_OUTPUT,
    FEEDER2_OUTPUT,
    OUTER_FEEDER_OUTPUT,
    SOLAR_PUMP_OUTPUT,
    FIREPLACE_PUMP_OUTPUT,
    GCZ_CONTACT,
    BLOW_FAN1_OUTPUT,
    BLOW_FAN2_OUTPUT,
]


def from_bytes(
    message: bytearray, offset: int = 0, data: Optional[Records] = None
) -> Tuple[Records, int]:
    """Parse bytes and return message data and offset."""
    if data is None:
        data = {}

    outputs = util.unpack_ushort(message[offset : offset + 4])
    for index, output in enumerate(OUTPUTS):
        data[output] = bool(outputs & int(math.pow(2, index)))

    offset += 4

    return data, offset
