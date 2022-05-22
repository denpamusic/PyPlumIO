"""Contains UID structure parser."""

from typing import Final, List, Tuple

UID_BASE: Final = 32
UID_BASE_BITS: Final = 5
UID_CHAR_BITS: Final = 8


def from_bytes(message: bytearray, offset: int = 0) -> Tuple[str, int]:
    """Parses frame message into usable data.

    Keyword arguments:
        message -- message bytes
        offset -- current data offset
    """
    uid_length = message[offset]
    offset += 1
    uid = message[offset : uid_length + offset].decode()
    offset += uid_length
    input_ = uid + uid_stamp(uid)
    input_length = len(input_) * UID_CHAR_BITS
    output: List[str] = []
    output_length = input_length // UID_BASE_BITS
    if input_length % UID_BASE_BITS:
        output_length += 1

    conv_int = 0
    conv_size = 0
    j = 0
    for _ in range(output_length):
        if conv_size < UID_BASE_BITS and j < len(input_):
            conv_int += ord(input_[j]) << conv_size
            conv_size += UID_CHAR_BITS
            j += 1

        char_code = conv_int % UID_BASE
        conv_int //= UID_BASE
        conv_size -= UID_BASE_BITS
        output.insert(0, uid_5bits_to_char(char_code))

    return "".join(output), offset


def uid_stamp(message: str) -> str:
    """Calculates UID stamp.

    Keyword arguments:
        message -- uid message
    """
    crc_ = 0xA3A3
    for byte in message:
        int_ = ord(byte)
        crc_ = uid_byte(crc_ ^ int_)

    return chr(crc_ % 256) + chr((crc_ // 256) % 256)


def uid_byte(byte: int) -> int:
    """Calculate CRC for single byte.

    Keyword arguments:
        byte - byte to calculate CRC
    """
    for _ in range(8):
        byte = (byte >> 1) ^ 0xA001 if byte & 1 else byte >> 1

    return byte


def uid_5bits_to_char(number: int) -> str:
    """Converts 5 bits from UID to ASCII character.

    Keyword arguments:
        number -- byte for conversion
    """
    if number < 0 or number >= 32:
        return "#"

    if number < 10:
        return chr(ord("0") + number)

    char = chr(ord("A") + number - 10)

    return "Z" if char == "O" else char
