"""Contains thermostats structure parser."""

from pyplumio import util


def from_bytes(message: bytearray, offset: int = 0) -> (list, int):
    """Parses frame message into usable data.

    Keyword arguments:
    message -- ecoNET message
    offset -- current data offset
    """
    data = []
    if message[offset] == 0xFF:
        offset += 1
        return offset

    therm_contacts = message[offset]
    offset += 1
    therm_number = message[offset]
    offset += 1
    if therm_number > 0:
        contact_mask = 1
        schedule_mask = 1 << 3
        for therm in range(1, therm_number + 1):
            therm = {}
            therm["ecoSterContacts"] = bool(therm_contacts & contact_mask)
            therm["ecoSterDaySched"] = bool(therm_contacts & schedule_mask)
            therm["ecoSterMode"] = bool(message[offset])
            therm["ecoSterTemp"] = util.unpack_float(message[offset + 1 : offset + 5])[
                0
            ]
            therm["ecoSterSetTemp"] = util.unpack_float(
                message[offset + 5 : offset + 9]
            )[0]
            data.append(therm)
            offset += 9
            contact_mask = contact_mask << 1
            schedule_mask = schedule_mask << 1

    return data, offset
