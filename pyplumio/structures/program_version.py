"""Contains a program version decoder."""
from __future__ import annotations

from dataclasses import dataclass
import struct
from typing import Any, Final

from pyplumio._version import __version_tuple__
from pyplumio.structures import Structure
from pyplumio.utils import ensure_dict

ATTR_VERSION: Final = "version"

VERSION_INFO_SIZE: Final = 15

SOFTWARE_VERSION: str = ".".join(str(x) for x in __version_tuple__[0:3])

struct_program_version = struct.Struct("<2sB2s3s3HB")


@dataclass
class VersionInfo:
    """Represents a version info provided in program version response."""

    software: str = SOFTWARE_VERSION
    struct_tag: bytes = b"\xFF\xFF"
    struct_version: int = 5
    device_id: bytes = b"\x7A\x00"
    processor_signature: bytes = b"\x00\x00\x00"


class ProgramVersionStructure(Structure):
    """Represents a program version data structure."""

    __slots__ = ()

    def encode(self, data: dict[str, Any]) -> bytearray:
        """Encode data to the bytearray message."""
        message = bytearray(struct_program_version.size)
        version_info = data[ATTR_VERSION] if ATTR_VERSION in data else VersionInfo()
        struct_program_version.pack_into(
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
        self, message: bytearray, offset: int = 0, data: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], int]:
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
        ] = struct_program_version.unpack_from(message)
        version_info.software = ".".join(
            map(str, [software_version1, software_version2, software_version3])
        )

        return (
            ensure_dict(data, {ATTR_VERSION: version_info}),
            offset + VERSION_INFO_SIZE,
        )
