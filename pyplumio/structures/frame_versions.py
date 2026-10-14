"""Contains a frame versions structure decoder."""

from __future__ import annotations

from contextlib import suppress
from typing import Any, Final

from pyplumio.const import FrameType
from pyplumio.data_types import UnsignedShort
from pyplumio.structures import StructureDecoder

ATTR_FRAME_VERSIONS: Final = "frame_versions"


class FrameVersionsStructure(StructureDecoder):
    """Represents a frame version data structure."""

    def _unpack_frame_versions(self, message: bytearray) -> tuple[FrameType | int, int]:
        """Unpack frame versions."""
        frame_type = message[self._offset]
        self._offset += 1
        version = UnsignedShort.from_bytes(message, self._offset)
        self._offset += version.size
        with suppress(ValueError):
            frame_type = FrameType(frame_type)

        return frame_type, version.value

    def decode(self, message: bytearray, data: dict[str, Any], offset: int = 0) -> None:
        """Decode bytes and return message data and offset."""
        frame_versions = message[offset]
        self._offset = offset + 1
        data[ATTR_FRAME_VERSIONS] = dict(
            self._unpack_frame_versions(message) for _ in range(frame_versions)
        )


__all__ = ["ATTR_FRAME_VERSIONS", "FrameVersionsStructure"]
