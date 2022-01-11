"""Contains frame versions structure parser."""

from pyplumio import util


def from_bytes(message: bytearray, offset: int = 0) -> (list, int):
    """Parses frame message into usable data.

    Keyword arguments:
    message -- ecoNET message
    offset -- current data offset
    """
    data = {}
    frames_number = message[offset]
    offset += 1
    for _ in range(frames_number):
        frame_type = message[offset]
        version = util.unpack_ushort(message[offset + 1 : offset + 3])
        data[frame_type] = version
        offset += 3

    return data, offset
