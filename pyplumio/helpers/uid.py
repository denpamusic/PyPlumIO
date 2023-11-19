"""Contains an UID helpers."""
from __future__ import annotations

from functools import reduce
from typing import Final

CRC: Final = 0xA3A3
POLYNOMIAL: Final = 0xA001


def decode_uid(buffer: bytes) -> str:
    """Decode an UID string."""
    return _base5(buffer + _crc16(buffer))


def _base5(buffer: bytes) -> str:
    """Encode bytes to a base5 encoded string."""
    key_string = "0123456789ABCDEFGHIJKLMNZPQRSTUV"
    number = int.from_bytes(buffer, byteorder="little")
    output = ""
    while number:
        output = key_string[number & 0b00011111] + output
        number >>= 5

    return output


def _crc16(buffer: bytes) -> bytes:
    """Return a CRC 16."""
    crc16 = reduce(_crc16_byte, buffer, CRC)
    return crc16.to_bytes(byteorder="little", length=2)


def _crc16_byte(crc: int, byte: int) -> int:
    """Add a byte to the CRC."""
    crc ^= byte
    for _ in range(8):
        crc = (crc >> 1) ^ POLYNOMIAL if crc & 1 else crc >> 1

    return crc
