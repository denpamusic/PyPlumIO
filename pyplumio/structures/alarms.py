"""Contains alarms structure parser."""

from typing import Any, Dict, Final, Tuple

ALARMS: Final = "alarms"


def from_bytes(
    message: bytearray, offset: int = 0, data: Dict[str, Any] = None
) -> Tuple[Dict, int]:
    """Parses frame message into usable data.

    Keyword arguments:
        message -- message bytes
        offset -- current data offset
    """
    if data is None:
        data = {}

    alarms = []
    alarms_number = message[offset]
    for i in range(alarms_number):
        alarms.append(message[offset + i])

    offset += alarms_number + 1
    data[ALARMS] = alarms

    return data, offset
