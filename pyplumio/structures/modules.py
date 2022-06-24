"""Contains modules structure parser."""
from __future__ import annotations

import struct
from typing import Any, Dict, Final, Optional, Tuple

from pyplumio.constants import DATA_MODULES
from pyplumio.helpers.product_info import ConnectedModules

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
    message: bytearray, offset: int = 0, data: Optional[Dict[str, Any]] = None
) -> Tuple[Dict[str, Any], int]:
    """Parse bytes and return message data and offset."""
    if data is None:
        data = {}

    connected_modules = ConnectedModules()
    for module_name in MODULES:
        module_version, offset = _get_module_version(module_name, message, offset)
        setattr(connected_modules, module_name, module_version)

    data[DATA_MODULES] = connected_modules

    return data, offset


def _get_module_version(
    module_name: str, message: bytearray, offset: int = 0
) -> Tuple[Optional[str], int]:
    """Get module version from a message."""
    if message[offset] == 0xFF:
        return None, (offset + 1)

    version_data = struct.unpack("<BBB", message[offset : offset + 3])
    module_version = ".".join(str(i) for i in version_data)
    offset += 3

    if module_name == MODULE_A:
        vendor_code, vendor_version = struct.unpack("<BB", message[offset : offset + 2])
        module_version += f".{chr(vendor_code)}{str(vendor_version)}"
        offset += 2

    return module_version, offset
