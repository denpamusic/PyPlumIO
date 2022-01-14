"""Contains outputs structure parser."""

from pyplumio.constants import STATUSES


def from_bytes(message: bytearray, offset: int = 0, data: dict = None) -> (dict, int):
    """Parses frame message into usable data.

    Keyword arguments:
    message -- ecoNET message
    offset -- current data offset
    """
    if data is None:
        data = {}

    for index, status in enumerate(STATUSES):
        data[status] = message[offset + index]

    offset += 4

    return data, offset
