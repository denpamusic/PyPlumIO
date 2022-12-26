"""Contains various helper methods."""
from __future__ import annotations

import functools
import socket
import struct
from typing import Dict, Optional

from pyplumio.const import BYTE_UNDEFINED
from pyplumio.helpers.typing import ParameterDataType

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
    """Return the checksum."""
    return functools.reduce(lambda x, y: x ^ y, data)


def unpack_ushort(data: bytes) -> int:
    """Unpack a unsigned short number."""
    return int.from_bytes(data, byteorder="little", signed=False)


def unpack_string(data: bytearray, offset: int = 0) -> str:
    """Unpack a string."""
    strlen = data[offset]
    offset += 1
    return data[offset : offset + strlen + 1].decode()


def unpack_parameter(
    data: bytearray, offset: int = 0, size: int = 1
) -> Optional[ParameterDataType]:
    """Unpack a device parameter."""
    if not check_parameter(data[offset : offset + size * 3]):
        return None

    value = unpack_ushort(data[offset : offset + size])
    min_value = unpack_ushort(data[offset + size : offset + 2 * size])
    max_value = unpack_ushort(data[offset + 2 * size : offset + 3 * size])

    return value, min_value, max_value


def check_parameter(data: bytearray) -> bool:
    """Check if parameter contains any bytes besides 0xFF."""
    return any(x for x in data if x != BYTE_UNDEFINED)


def ip4_to_bytes(address: str) -> bytes:
    """Convert ip4 address to bytes."""
    return socket.inet_aton(address)


def ip4_from_bytes(data: bytes) -> str:
    """Convert bytes to ip4 address."""
    return socket.inet_ntoa(data)


def ip6_to_bytes(address: str) -> bytes:
    """Convert ip6 address to bytes."""
    return socket.inet_pton(socket.AF_INET6, address)


def ip6_from_bytes(data: bytes) -> str:
    """Convert bytes to ip6 address."""
    return socket.inet_ntop(socket.AF_INET6, data)


def to_camelcase(text: str, overrides: Dict[str, str] = None) -> str:
    """Convert snake_case to CamelCase."""
    if overrides is None:
        return "".join((x.capitalize() or "_") for x in text.split("_"))

    return "".join(
        (x.capitalize() or "_") if x.lower() not in overrides else overrides[x.lower()]
        for x in text.split("_")
    )
