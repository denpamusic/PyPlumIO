"""Contains alarms structure parser."""
from __future__ import annotations

from typing import Any, Dict, Final, Optional, Tuple

ALARMS: Final = "alarms"


def from_bytes(
    message: bytearray, offset: int = 0, data: Optional[Dict[str, Any]] = None
) -> Tuple[Dict, int]:
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
