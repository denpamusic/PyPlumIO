"""Contains variable string structure parser."""
from __future__ import annotations

from typing import Tuple


def from_bytes(message: bytearray, offset: int = 0) -> Tuple[str, int]:
    """Parse bytes and return message data and offset."""
    string_length = message[offset]
    offset += 1
    string = message[offset : offset + string_length + 1].decode()
    offset += string_length + 1

    return string, offset
