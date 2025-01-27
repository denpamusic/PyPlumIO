"""Contains UID helpers."""

from __future__ import annotations

from functools import reduce
from typing import Final

CRC: Final = 0xA3A3
POLYNOMIAL: Final = 0xA001
BASE5_KEY: Final = "0123456789ABCDEFGHIJKLMNZPQRSTUV"


def decode_uid(buffer: bytes) -> str:
    """Decode an UID string."""
    return _base5(buffer + _crc16(buffer))


def _base5(buffer: bytes) -> str:
    """Encode bytes to a base5 encoded string."""
    number = int.from_bytes(buffer, byteorder="little")
    output = []
    while number:
        output.append(BASE5_KEY[number & 0b00011111])
        number >>= 5

    return "".join(reversed(output))


def _crc16(buffer: bytes) -> bytes:
    """Return a CRC 16."""
    crc16 = reduce(_crc16_byte, buffer, CRC)
    return crc16.to_bytes(length=2, byteorder="little")


def _crc16_byte(crc: int, byte: int) -> int:
    """Add a byte to the CRC."""
    crc ^= byte
    for _ in range(8):
        crc = (crc >> 1) ^ POLYNOMIAL if crc & 1 else crc >> 1

    return crc
