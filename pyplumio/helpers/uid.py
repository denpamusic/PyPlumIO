"""Contains an UID helpers."""
from __future__ import annotations

from functools import reduce
from typing import Final


def unpack_uid(buffer: bytearray, offset: int = 0) -> str:
    """Decode and return a complete UID string from the buffer."""
    length = buffer.pop(offset)
    uid = buffer[offset : length + offset]
    del buffer[offset : length + offset]

    return _base5(uid + _crc16(uid))


def _base5(data: bytes) -> str:
    """Encode bytes to a base5 encoded string."""
    key_string = "0123456789ABCDEFGHIJKLMNZPQRSTUV"
    number = int.from_bytes(data, byteorder="little")
    output = ""
    while number:
        output = key_string[number & 0b00011111] + output
        number >>= 5

    return output


CRC: Final = 0xA3A3
POLYNOMIAL: Final = 0xA001


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
