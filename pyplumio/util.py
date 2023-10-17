"""Contains various utility methods."""
from __future__ import annotations

import functools
import socket
import struct

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
    """Return a checksum."""
    return functools.reduce(lambda x, y: x ^ y, data)


def unpack_ushort(data: bytes) -> int:
    """Unpack a unsigned short number."""
    return int.from_bytes(data, byteorder="little", signed=False)


def unpack_string(data: bytearray, offset: int = 0) -> str:
    """Unpack a string."""
    strlen = data[offset]
    offset += 1
    return data[offset : offset + strlen + 1].decode()


def ip4_to_bytes(address: str) -> bytes:
    """Convert an IPv4 address to bytes."""
    return socket.inet_aton(address)


def ip4_from_bytes(data: bytes) -> str:
    """Convert bytes to an IPv4 address."""
    return socket.inet_ntoa(data)


def ip6_to_bytes(address: str) -> bytes:
    """Convert an IPv6 address to bytes."""
    return socket.inet_pton(socket.AF_INET6, address)


def ip6_from_bytes(data: bytes) -> str:
    """Convert bytes to an IPv6 address."""
    return socket.inet_ntop(socket.AF_INET6, data)


def to_camelcase(text: str, overrides: dict[str, str] = None) -> str:
    """Convert snake_case to CamelCase."""
    if overrides is None:
        return "".join((x.capitalize() or "_") for x in text.split("_"))

    return "".join(
        (x.capitalize() or "_") if x.lower() not in overrides else overrides[x.lower()]
        for x in text.split("_")
    )
