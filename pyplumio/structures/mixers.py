"""Contains mixers structure parser."""

from pyplumio import util


def from_bytes(message: bytearray, offset: int = 0) -> (list, int):
    """Parses frame message into usable data.

    Keyword arguments:
    message -- ecoNET message
    offset -- current data offset
    """
    data = []
    mixers_number = message[offset]
    offset += 1
    if mixers_number > 0:
        for _ in range(1, mixers_number + 1):
            mixer = {}
            mixer["mixerTemp"] = util.unpack_float(message[offset : offset + 4])[0]
            mixer["mixerSetTemp"] = message[offset + 4]
            mixer_outputs = message[offset + 6]
            mixer["mixerPumpWorks"] = bool(mixer_outputs & 0x01)
            data.append(mixer)
            offset += 8

    return data, offset
