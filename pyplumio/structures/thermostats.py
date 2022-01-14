"""Contains thermostats structure parser."""

from pyplumio import util
from pyplumio.constants import (
    DATA_THERMOSTATS,
    ECOSTER_CONTACTS,
    ECOSTER_MODE,
    ECOSTER_SCHEDULE,
    ECOSTER_TARGET,
    ECOSTER_TEMP,
)


def from_bytes(message: bytearray, offset: int = 0, data: dict = None) -> (list, int):
    """Parses frame message into usable data.

    Keyword arguments:
    message -- ecoNET message
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
        for therm in range(1, therm_number + 1):
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

    data[DATA_THERMOSTATS] = thermostats

    return data, offset
