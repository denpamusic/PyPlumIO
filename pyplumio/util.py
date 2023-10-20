"""Contains various utility methods."""
from __future__ import annotations

from functools import reduce
import struct

# Frame header packer and unpacker.
pack_header = struct.Struct("<BH4B").pack_into
unpack_header = struct.Struct("<BH4B").unpack_from


def bcc(data: bytes) -> int:
    """Return a block check character."""
    return reduce(lambda x, y: x ^ y, data)


def to_camelcase(text: str, overrides: dict[str, str] = None) -> str:
    """Convert snake_case to CamelCase."""
    if overrides is None:
        return "".join((x.capitalize() or "_") for x in text.split("_"))

    return "".join(
        (x.capitalize() or "_") if x.lower() not in overrides else overrides[x.lower()]
        for x in text.split("_")
    )
