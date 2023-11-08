"""Contains a frame versions structure decoder."""
from __future__ import annotations

from typing import Final

from pyplumio.const import FrameType
from pyplumio.helpers.data_types import UnsignedShort
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_FRAME_VERSIONS: Final = "frame_versions"


class FrameVersionsStructure(StructureDecoder):
    """Represents a frame version data structure."""

    _offset: int

    def _unpack_frame_versions(self, message: bytearray) -> tuple[FrameType | int, int]:
        """Unpack frame versions."""
        try:
            frame_type = message[self._offset]
            frame_type = FrameType(frame_type)
        except ValueError:
            pass

        self._offset += 1
        version = UnsignedShort.from_bytes(message, self._offset)
        self._offset += version.size
        return frame_type, version.value

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        frame_versions = message[offset]
        self._offset = offset + 1
        return (
            ensure_dict(
                data,
                {
                    ATTR_FRAME_VERSIONS: dict(
                        self._unpack_frame_versions(message)
                        for _ in range(frame_versions)
                    )
                },
            ),
            self._offset,
        )
