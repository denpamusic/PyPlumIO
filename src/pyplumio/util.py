"""Contains various helper methods."""

import functools
import socket
import struct

DEGREE_SIGN = "\N{DEGREE SIGN}"
unpack_float = struct.Struct("<f").unpack
pack_header = struct.Struct("<BH4B").pack_into
unpack_header = struct.Struct("<BH4B").unpack_from


def crc(data: bytearray) -> int:
    """Calculates frame checksum.

    Keyword arguments:
    data - data to calculate checksum for
    """
    return functools.reduce(lambda x, y: x ^ y, data)


def to_hex(data: bytearray) -> str:
    """Converts bytearray to list of hex strings.

    Keyword arguments:
    data - data for conversion
    """
    return [f"{data[i]:02X}" for i in range(0, len(data))]


def unpack_ushort(data: bytearray) -> int:
    """Unpacks unsigned short number from bytes.

    Keyword arguments:
    data - bytes to unpack number from
    """
    return int.from_bytes(data, byteorder="little", signed=False)


def ip_to_bytes(address: str) -> bytearray:
    """Converts ip address to bytes.

    Keyword arguments:
    address -- ip address as string
    """
    return socket.inet_aton(address)


def ip_from_bytes(data: bytearray) -> str:
    """Converts ip address from bytes to string representation.

    Keyword arguments:
    data -- 4 bytes to convert
    """
    return socket.inet_ntoa(data)


def merge(defaults: dict, options: dict) -> dict:
    """Merges two dictionary with options overriding defaults.

    Keyword arguments:
    defaults -- dictionary of defaults
    options -- dictionary containing options for overriding defaults
    """
    if not options:
        # Options is empty.
        return defaults

    for key in defaults.keys():
        if key not in options:
            options[key] = defaults[key]

    return options


def check_parameter(data: bytearray) -> bool:
    """Checks if parameter contains any bytes besides 0xFF.

    Keyword arguments:
    data -- parameter bytes
    """
    for byte in data:
        if byte != 0xFF:
            return True

    return False


def uid_stamp(message: str) -> str:
    """Calculates UID stamp.

    Keyword arguments:
    message -- uid message
    """
    crc_ = 0xA3A3
    for byte in message:
        int_ = ord(byte)
        crc_ = crc_ ^ int_
        for _ in range(8):
            if crc_ & 1:
                crc_ = (crc_ >> 1) ^ 0xA001
            else:
                crc_ = crc_ >> 1

    return chr(crc_ % 256) + chr((crc_ // 256) % 256)


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
