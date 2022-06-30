"""Contains alarms structure parser."""
from __future__ import annotations

from typing import Final, Optional, Tuple

from pyplumio.helpers.typing import Records

ALARMS: Final = "alarms"


def from_bytes(
    message: bytearray, offset: int = 0, data: Optional[Records] = None
) -> Tuple[Records, int]:
    """Parse bytes and return message data and offset."""
    if data is None:
        data = {}

    alarms = []
    alarms_number = message[offset]
    for i in range(alarms_number):
        alarms.append(message[offset + i])

    offset += alarms_number + 1
    data[ALARMS] = alarms

    return data, offset
