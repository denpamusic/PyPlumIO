"""Contains a program version decoder."""

from __future__ import annotations

from dataclasses import dataclass
import struct
from typing import Any, Final

from pyplumio import version_tuple
from pyplumio.structures import Structure

ATTR_VERSION: Final = "version"

VERSION_INFO_SIZE: Final = 15

SOFTWARE_VERSION: Final = ".".join(str(x) for x in version_tuple[0:3])

struct_program_version = struct.Struct("<2sB2s3s3HB")


@dataclass(slots=True)
class VersionInfo:
    """Represents a version info provided in program version response."""

    software: str = SOFTWARE_VERSION
    struct_tag: bytes = b"\xff\xff"
    struct_version: int = 5
    device_id: bytes = b"\x7a\x00"
    processor_signature: bytes = b"\x00\x00\x00"


class ProgramVersionStructure(Structure):
    """Represents a program version data structure."""

    __slots__ = ()

    def encode(self, data: dict[str, Any]) -> bytes:
        """Encode data to bytes."""
        message = bytearray(struct_program_version.size)
        version_info: VersionInfo = data.get(ATTR_VERSION, VersionInfo())
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

        return bytes(message)

    def decode(self, message: bytes, data: dict[str, Any], offset: int = 0) -> None:
        """Decode bytes and return message data and offset."""
        (
            struct_tag,
            struct_version,
            device_id,
            processor_signature,
            software1,
            software2,
            software3,
            _,  # recipient
        ) = struct_program_version.unpack_from(message)
        self._offset = offset + VERSION_INFO_SIZE
        data[ATTR_VERSION] = VersionInfo(
            software=".".join(map(str, [software1, software2, software3])),
            struct_tag=struct_tag,
            struct_version=struct_version,
            device_id=device_id,
            processor_signature=processor_signature,
        )


__all__ = ["ATTR_VERSION", "VersionInfo", "ProgramVersionStructure"]
