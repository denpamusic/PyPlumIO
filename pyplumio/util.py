"""Contains various utility methods."""
from __future__ import annotations

import functools
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


def to_camelcase(text: str, overrides: dict[str, str] = None) -> str:
    """Convert snake_case to CamelCase."""
    if overrides is None:
        return "".join((x.capitalize() or "_") for x in text.split("_"))

    return "".join(
        (x.capitalize() or "_") if x.lower() not in overrides else overrides[x.lower()]
        for x in text.split("_")
    )
