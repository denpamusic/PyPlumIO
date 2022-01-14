"""Contains mixers structure parser."""

from pyplumio import util
from pyplumio.constants import DATA_MIXERS, MIXER_PUMP, MIXER_TARGET, MIXER_TEMP


def from_bytes(message: bytearray, offset: int = 0, data: dict = None) -> (list, int):
    """Parses frame message into usable data.

    Keyword arguments:
    message -- ecoNET message
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
