"""Contains versions structure parser."""

import struct
from typing import Any, Dict, Tuple

from pyplumio.constants import MODULE_A, MODULES


def from_bytes(
    message: bytearray, offset: int = 0, data: Dict[str, Any] = None
) -> Tuple[Dict[str, Any], int]:
    """Parses frame message into usable data.

    Keyword arguments:
        message -- message bytes
        offset -- current data offset
    """
    if data is None:
        data = {}

    for module in MODULES:
        if message[offset] == 0xFF:
            offset += 1
            continue

        if module == MODULE_A:
            version_data = struct.unpack("<BBBBB", message[offset : offset + 5])
            version1 = ".".join(map(str, version_data[:3]))
            version2 = "." + chr(version_data[3])
            version3 = str(version_data[4])
            data[module] = version1 + version2 + version3
            offset += 5
            continue

        data[module] = ".".join(
            map(str, struct.unpack("<BBB", message[offset : offset + 3]))
        )
        offset += 3

    return data, offset
