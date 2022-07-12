"""Contains version info dataclass."""
from __future__ import annotations

from dataclasses import dataclass

from pyplumio.version import __version__


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
