"""Contains various helper methods."""

import functools
import socket
import struct
from typing import Any, Dict, List, Optional, Tuple

DEGREE_SIGN = "\N{DEGREE SIGN}"
unpack_float = struct.Struct("<f").unpack
unpack_char = struct.Struct("<b").unpack
unpack_short = struct.Struct("<h").unpack
unpack_int = struct.Struct("<i").unpack
unpack_uint = struct.Struct("<I").unpack
unpack_double = struct.Struct("<d").unpack
unpack_int64 = struct.Struct("<q").unpack
unpack_uint64 = struct.Struct("<Q").unpack
pack_header = struct.Struct("<BH4B").pack_into
unpack_header = struct.Struct("<BH4B").unpack_from


def crc(data: bytes) -> int:
    """Calculates frame checksum.

    Keyword arguments:
        data -- data to calculate checksum for
    """
    return functools.reduce(lambda x, y: x ^ y, data)


def to_hex(data: bytes) -> List[str]:
    """Converts bytes to list of hex strings.

    Keyword arguments:
        data -- data for conversion
    """
    return [f"{data[i]:02X}" for i in range(0, len(data))]


def unpack_ushort(data: bytes) -> int:
    """Unpacks unsigned short number from bytes.

    Keyword arguments:
        data -- bytes to unpack number from
    """
    return int.from_bytes(data, byteorder="little", signed=False)


def unpack_parameter(
    data: bytearray, offset: int, size: int = 1
) -> Optional[Tuple[int, int, int]]:
    """Unpacks parameter.

    Keyword arguments:
        data -- bytes to unpack number from
        offset -- data offset
        size -- parameter size in bytes
    """

    if not check_parameter(data[offset : offset + size * 3]):
        return None

    value = unpack_ushort(data[offset : offset + size])
    min_ = unpack_ushort(data[offset + size : offset + 2 * size])
    max_ = unpack_ushort(data[offset + 2 * size : offset + 3 * size])

    return value, min_, max_


def ip4_to_bytes(address: str) -> bytes:
    """Converts ip4 address to bytes.

    Keyword arguments:
        address -- ip address as string
    """
    return socket.inet_aton(address)


def ip4_from_bytes(data: bytes) -> str:
    """Converts ip4 address from bytes to string representation.

    Keyword arguments:
        data -- address bytes to convert
    """
    return socket.inet_ntoa(data)


def ip6_to_bytes(address: str) -> bytes:
    """Converts ip6 address to bytes.

    Keyword arguments:
        address -- ip address as string
    """
    return socket.inet_pton(socket.AF_INET6, address)


def ip6_from_bytes(data: bytes) -> str:
    """Converts ip4 address from bytes to string representation.

    Keyword arguments:
        data -- address bytes to convert
    """
    return socket.inet_ntop(socket.AF_INET6, data)


def merge(defaults: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
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
            crc_ = (crc_ >> 1) ^ 0xA001 if crc_ & 1 else crc_ >> 1

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


def make_list(data: Dict[Any, Any], include_keys: bool = True) -> str:
    """Converts dictionary to string.

    Keyword arguments:
        data -- dictionary to convert to string
        include_keys -- determines if keys should be included
    """

    output = ""
    for k, v in data.items():
        output += f"- {k}: {v}\n" if include_keys else f"- {v}\n"

    return output.rstrip()
