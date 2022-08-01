"""Contains modules structure decoder."""
from __future__ import annotations

import struct
from typing import Final, Optional, Tuple

from pyplumio.const import ATTR_MODULES
from pyplumio.helpers.product_info import ConnectedModules
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, make_device_data

MODULE_A: Final = "module_a"
MODULE_B: Final = "module_b"
MODULE_C: Final = "module_c"
MODULE_LAMBDA: Final = "module_lambda"
MODULE_ECOSTER: Final = "module_ecoster"
MODULE_PANEL: Final = "module_panel"
MODULES: Tuple[str, ...] = (
    MODULE_A,
    MODULE_B,
    MODULE_C,
    MODULE_LAMBDA,
    MODULE_ECOSTER,
    MODULE_PANEL,
)


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


class ModulesStructure(StructureDecoder):
    """Represents modules data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        connected_modules = ConnectedModules()
        for module_name in MODULES:
            module_version, offset = _get_module_version(module_name, message, offset)
            setattr(connected_modules, module_name, module_version)

        return make_device_data(data, {ATTR_MODULES: connected_modules}), offset
