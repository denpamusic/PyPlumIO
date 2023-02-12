"""Contains program version decoder."""
from __future__ import annotations

from dataclasses import dataclass
import struct
from typing import Final

from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import Structure, ensure_device_data
from pyplumio.version import __version__

ATTR_VERSION: Final = "version"


def _formated_version(version=__version__) -> str:
    """Format version for program version response."""
    version_parts = version.split(".")
    return ".".join(version_parts[0:3])


@dataclass
class VersionInfo:
    """Represents version info provided in program version response."""

    software: str = _formated_version()
    struct_tag: bytes = b"\xFF\xFF"
    struct_version: int = 5
    device_id: bytes = b"\x7A\x00"
    processor_signature: bytes = b"\x00\x00\x00"


class ProgramVersionStructure(Structure):
    """Represents program version data structure."""

    def encode(self, data: EventDataType) -> bytearray:
        """Encode device data to bytearray message."""
        message = bytearray(15)
        version_info = data[ATTR_VERSION] if ATTR_VERSION in data else VersionInfo()
        struct.pack_into(
            "<2sB2s3s3HB",
            message,
            0,
            version_info.struct_tag,
            version_info.struct_version,
            version_info.device_id,
            version_info.processor_signature,
            *map(int, version_info.software.split(".", 2)),
            self.frame.sender,
        )
        return message

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        version_info = VersionInfo()
        [
            version_info.struct_tag,
            version_info.struct_version,
            version_info.device_id,
            version_info.processor_signature,
            software_version1,
            software_version2,
            software_version3,
            self.frame.recipient,
        ] = struct.unpack_from("<2sB2s3s3HB", message)
        version_info.software = ".".join(
            map(str, [software_version1, software_version2, software_version3])
        )

        return ensure_device_data(data, {ATTR_VERSION: version_info}), offset + 15
