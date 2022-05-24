"""Contains mixers structure parser."""

from typing import Any, Dict, Final, Tuple

from pyplumio import util
from pyplumio.constants import DATA_MIXERS

MIXER_TEMP: Final = "temp"
MIXER_TARGET: Final = "target"
MIXER_PUMP: Final = "pump"
MIXER_DATA: Final = (
    MIXER_TEMP,
    MIXER_TARGET,
    MIXER_PUMP,
)


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

    mixers = []
    mixers_number = message[offset]
    offset += 1
    if mixers_number > 0:
        for _ in range(1, mixers_number + 1):
            mixer = {}
            mixer[MIXER_TEMP] = util.unpack_float(message[offset : offset + 4])[0]
            mixer[MIXER_TARGET] = message[offset + 4]
            mixer_outputs = message[offset + 6]
            mixer[MIXER_PUMP] = bool(mixer_outputs & 0x01)
            mixers.append(mixer)
            offset += 8

    data[DATA_MIXERS] = mixers

    return data, offset
