"""Contains thermostats structure parser."""

from typing import Any, Dict, Final, Tuple

from pyplumio import util

THERMOSTATS: Final = "thermostats"
ECOSTER_CONTACTS: Final = "contacts"
ECOSTER_SCHEDULE: Final = "schedule"
ECOSTER_MODE: Final = "mode"
ECOSTER_TEMP: Final = "temp"
ECOSTER_TARGET: Final = "target"


def from_bytes(
    message: bytearray, offset: int = 0, data: Dict[str, Any] = None
) -> Tuple[Dict[str, Any], int]:
    """Parses frame message into usable data.

    Keyword arguments:
        message -- message bytes
        offset -- current data offset
    """
    if data is None:
        data = {}

    if message[offset] == 0xFF:
        offset += 1
        return data, offset

    thermostats = []
    therm_contacts = message[offset]
    offset += 1
    therm_number = message[offset]
    offset += 1
    if therm_number > 0:
        contact_mask = 1
        schedule_mask = 1 << 3
        for _ in range(1, therm_number + 1):
            therm = {}
            therm[ECOSTER_CONTACTS] = bool(therm_contacts & contact_mask)
            therm[ECOSTER_SCHEDULE] = bool(therm_contacts & schedule_mask)
            therm[ECOSTER_MODE] = bool(message[offset])
            therm[ECOSTER_TEMP] = util.unpack_float(message[offset + 1 : offset + 5])[0]
            therm[ECOSTER_TARGET] = util.unpack_float(message[offset + 5 : offset + 9])[
                0
            ]
            thermostats.append(therm)
            offset += 9
            contact_mask = contact_mask << 1
            schedule_mask = schedule_mask << 1

    data[THERMOSTATS] = thermostats

    return data, offset
