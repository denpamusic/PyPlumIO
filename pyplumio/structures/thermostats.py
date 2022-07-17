"""Contains thermostats structure parser."""
from __future__ import annotations

from typing import Final, List, Optional, Tuple

from pyplumio import util
from pyplumio.const import ATTR_THERMOSTATS
from pyplumio.helpers.typing import DeviceDataType

ECOSTER_CONTACTS: Final = "contacts"
ECOSTER_SCHEDULE: Final = "schedule"
ECOSTER_MODE: Final = "mode"
ECOSTER_TEMP: Final = "temp"
ECOSTER_TARGET: Final = "target"


def from_bytes(
    message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
) -> Tuple[DeviceDataType, int]:
    """Parse bytes and return message data and offset."""
    if data is None:
        data = {}

    if message[offset] == 0xFF:
        offset += 1
        return data, offset

    thermostats: List[DeviceDataType] = []
    therm_contacts = message[offset]
    offset += 1
    therm_number = message[offset]
    offset += 1
    if therm_number > 0:
        contact_mask = 1
        schedule_mask = 1 << 3
        for _ in range(1, therm_number + 1):
            therm: DeviceDataType = {}
            therm[ECOSTER_CONTACTS] = bool(therm_contacts & contact_mask)
            therm[ECOSTER_SCHEDULE] = bool(therm_contacts & schedule_mask)
            therm[ECOSTER_MODE] = message[offset]
            therm[ECOSTER_TEMP] = util.unpack_float(message[offset + 1 : offset + 5])[0]
            therm[ECOSTER_TARGET] = util.unpack_float(message[offset + 5 : offset + 9])[
                0
            ]
            thermostats.append(therm)
            offset += 9
            contact_mask = contact_mask << 1
            schedule_mask = schedule_mask << 1

    data[ATTR_THERMOSTATS] = thermostats

    return data, offset
