"""Contains a program version decoder."""

from __future__ import annotations

from dataclasses import dataclass
import struct
from typing import Any, Final

from dataslots import dataslots

from pyplumio._version import __version_tuple__
from pyplumio.structures import Structure
from pyplumio.utils import ensure_dict

ATTR_VERSION: Final = "version"

VERSION_INFO_SIZE: Final = 15

SOFTWARE_VERSION: Final = ".".join(str(x) for x in __version_tuple__[0:3])

struct_program_version = struct.Struct("<2sB2s3s3HB")


@dataslots
@dataclass
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

    def encode(self, data: dict[str, Any]) -> bytearray:
        """Encode data to the bytearray message."""
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
        return message

    def decode(
        self, message: bytearray, offset: int = 0, data: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], int]:
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

        return (
            ensure_dict(
                data,
                {
                    ATTR_VERSION: VersionInfo(
                        software=".".join(map(str, [software1, software2, software3])),
                        struct_tag=struct_tag,
                        struct_version=struct_version,
                        device_id=device_id,
                        processor_signature=processor_signature,
                    )
                },
            ),
            offset + VERSION_INFO_SIZE,
        )


__all__ = ["ATTR_VERSION", "VersionInfo", "ProgramVersionStructure"]
