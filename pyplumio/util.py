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
    min_value = unpack_ushort(data[offset + size : offset + 2 * size])
    max_value = unpack_ushort(data[offset + 2 * size : offset + 3 * size])

    return value, min_value, max_value


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


def check_parameter(data: bytearray) -> bool:
    """Checks if parameter contains any bytes besides 0xFF.

    Keyword arguments:
        data -- parameter bytes
    """
    for byte in data:
        if byte != 0xFF:
            return True

    return False


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
