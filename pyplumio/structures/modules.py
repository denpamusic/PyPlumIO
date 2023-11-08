"""Contains a modules structure decoder."""
from __future__ import annotations

from dataclasses import dataclass
import struct
from typing import Final

from pyplumio.const import BYTE_UNDEFINED
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_MODULES: Final = "modules"
ATTR_MODULE_A: Final = "module_a"
ATTR_MODULE_B: Final = "module_b"
ATTR_MODULE_C: Final = "module_c"
ATTR_ECOLAMBDA: Final = "ecolambda"
ATTR_ECOSTER: Final = "ecoster"
ATTR_PANEL: Final = "panel"
MODULES: tuple[str, ...] = (
    ATTR_MODULE_A,
    ATTR_MODULE_B,
    ATTR_MODULE_C,
    ATTR_ECOLAMBDA,
    ATTR_ECOSTER,
    ATTR_PANEL,
)

struct_version = struct.Struct("<BBB")
struct_vendor = struct.Struct("<BB")


@dataclass
class ConnectedModules:
    """Represents a firmware version info for connected module."""

    module_a: str | None = None
    module_b: str | None = None
    module_c: str | None = None
    ecolambda: str | None = None
    ecoster: str | None = None
    panel: str | None = None


class ModulesStructure(StructureDecoder):
    """Represents a modules data structure."""

    _offset: int

    def _unpack_module_version(self, module: str, message: bytearray) -> str | None:
        """Unpack a module version."""
        if message[self._offset] == BYTE_UNDEFINED:
            self._offset += 1
            return None

        version_data = struct_version.unpack_from(message, self._offset)
        version = ".".join(str(i) for i in version_data)
        self._offset += struct_version.size

        if module == ATTR_MODULE_A:
            vendor_code, vendor_version = struct_vendor.unpack_from(
                message, self._offset
            )
            version += f".{chr(vendor_code) + str(vendor_version)}"
            self._offset += struct_vendor.size

        return version

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        self._offset = offset
        return (
            ensure_dict(
                data,
                {
                    ATTR_MODULES: ConnectedModules(
                        **{
                            module: self._unpack_module_version(module, message)
                            for module in MODULES
                        }
                    )
                },
            ),
            self._offset,
        )
