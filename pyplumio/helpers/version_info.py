"""Contains version info representation."""

from dataclasses import dataclass

from pyplumio.version import __version__


@dataclass
class VersionInfo:
    """Represents version info provided in program version response."""

    software: str = __version__
    struct_tag: bytes = b"\xFF\xFF"
    struct_version: int = 5
    device_id: bytes = b"\x7A\x00"
    processor_signature = b"\x00\x00\x00"
