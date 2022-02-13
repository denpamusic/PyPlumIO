"""Contains variable string structure parser."""

from typing import Tuple


def from_bytes(message: bytearray, offset: int = 0) -> Tuple[str, int]:
    """Parses frame message into usable data.

    Keyword arguments:
        message -- message bytes
        offset -- current data offset
    """
    string_length = message[offset]
    offset += 1
    string = message[offset : offset + string_length + 1].decode()
    offset += string_length + 1

    return string, offset
