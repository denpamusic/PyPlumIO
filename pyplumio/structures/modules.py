"""Contains versions structure parser."""

import struct
from typing import Any, Dict, Final, Tuple

MODULE_A: Final = "module_a"
MODULE_B: Final = "module_b"
MODULE_C: Final = "module_c"
MODULE_LAMBDA: Final = "module_lambda"
MODULE_ECOSTER: Final = "module_ecoster"
MODULE_PANEL: Final = "module_panel"
MODULES: Final = (
    MODULE_A,
    MODULE_B,
    MODULE_C,
    MODULE_LAMBDA,
    MODULE_ECOSTER,
    MODULE_PANEL,
)


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
            data[module] = None
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
