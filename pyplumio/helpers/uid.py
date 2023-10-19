"""Contains an UID helpers."""
from __future__ import annotations


def unpack_uid(message: bytearray, offset: int = 0) -> str:
    """Decode and return a complete UID string."""
    length = message[offset]
    offset += 1
    uid = message[offset : length + offset]

    return _encode_base5(uid + _uid_crc(uid))


def _encode_base5(data: bytes) -> str:
    """Encode bytes to a base5 encoded string."""
    key_string = "0123456789ABCDEFGHIJKLMNZPQRSTUV"
    number = int.from_bytes(data, "little")
    output = ""
    while number:
        output = key_string[number & 0b00011111] + output
        number >>= 5

    return output


def _uid_crc(message: bytes) -> bytes:
    """Return an UID CRC."""
    crc_value = 0xA3A3
    for byte in message:
        crc_value = _uid_byte(crc_value ^ byte)

    return crc_value.to_bytes(byteorder="little", length=2)


def _uid_byte(byte: int) -> int:
    """Return a byte CRC."""
    for _ in range(8):
        byte = (byte >> 1) ^ 0xA001 if byte & 1 else byte >> 1

    return byte
