"""Contains UID decoder."""
from __future__ import annotations

from collections import deque
from typing import Deque


def unpack_uid(message: bytearray, offset: int = 0) -> str:
    """Decode bytes and return message data and offset."""
    uid_length = message[offset]
    offset += 1
    uid = message[offset : uid_length + offset]
    uid += _uid_stamp(uid)

    return _encode_base5(uid)


def _encode_base5(data: bytes) -> str:
    """Encode data str to base5."""
    number = int.from_bytes(data, "little")
    ret: Deque[str] = deque()
    mask = (1 << 5) - 1
    while number:
        ret.appendleft(_digit_to_char(number & mask))
        number >>= 5

    return "".join(ret)


def _digit_to_char(digit: int) -> str:
    """Convert 5 bits from UID to ASCII character."""
    if digit < 10:
        return str(digit)

    char = chr(ord("A") + digit - 10)

    return "Z" if char == "O" else char


def _uid_stamp(message: bytes) -> bytes:
    """Return UID stamp."""
    crc_value = 0xA3A3
    for byte in message:
        crc_value = _uid_byte(crc_value ^ byte)

    return crc_value.to_bytes(byteorder="little", length=2)


def _uid_byte(byte: int) -> int:
    """Return CRC for a byte."""
    for _ in range(8):
        byte = (byte >> 1) ^ 0xA001 if byte & 1 else byte >> 1

    return byte
