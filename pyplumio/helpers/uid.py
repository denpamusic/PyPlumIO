"""Contains UID decoder."""
from __future__ import annotations


def unpack_uid(message: bytearray, offset: int = 0) -> str:
    """Decode and return uid string."""
    uid_length = message[offset]
    offset += 1
    uid = message[offset : uid_length + offset]

    return _encode_base5(uid + _uid_crc(uid))


def _encode_base5(data: bytes) -> str:
    """Encode bytes to base5 encided string."""
    key_string = "0123456789ABCDEFGHIJKLMNZPQRSTUV"
    number = int.from_bytes(data, "little")
    output: str = ""
    mask = (1 << 5) - 1
    while number:
        output = key_string[number & mask] + output
        number >>= 5

    return output


def _uid_crc(message: bytes) -> bytes:
    """Return UID crc."""
    crc_value = 0xA3A3
    for byte in message:
        crc_value = _uid_byte(crc_value ^ byte)

    return crc_value.to_bytes(byteorder="little", length=2)


def _uid_byte(byte: int) -> int:
    """Return CRC for a byte."""
    for _ in range(8):
        byte = (byte >> 1) ^ 0xA001 if byte & 1 else byte >> 1

    return byte
