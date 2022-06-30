"""Contains mixers structure parser."""
from __future__ import annotations

from collections.abc import MutableSequence
from typing import Final, Optional, Tuple

from pyplumio import util
from pyplumio.const import DATA_MIXER_SENSORS
from pyplumio.helpers.typing import Records

MIXER_TEMP: Final = "temp"
MIXER_TARGET_TEMP: Final = "target_temp"
MIXER_PUMP_OUTPUT: Final = "pump_output"
MIXER_DATA: Final = (
    MIXER_TEMP,
    MIXER_TARGET_TEMP,
    MIXER_PUMP_OUTPUT,
)


def from_bytes(
    message: bytearray, offset: int = 0, data: Optional[Records] = None
) -> Tuple[Records, int]:
    """Parse bytes and return message data and offset."""
    if data is None:
        data = {}

    mixers_number = message[offset]
    offset += 1
    if mixers_number == 0:
        return data, offset

    mixers: MutableSequence[Records] = []

    for _ in range(mixers_number):
        mixer = {}
        mixer[MIXER_TEMP] = util.unpack_float(message[offset : offset + 4])[0]
        mixer[MIXER_TARGET_TEMP] = message[offset + 4]
        mixer_outputs = message[offset + 6]
        mixer[MIXER_PUMP_OUTPUT] = bool(mixer_outputs & 0x01)
        mixers.append(mixer)
        offset += 8

    data[DATA_MIXER_SENSORS] = mixers

    return data, offset
