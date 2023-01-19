"""Contains frame versions structure decoder."""
from __future__ import annotations

from typing import Final, Optional, Tuple

from pyplumio import util
from pyplumio.const import FrameType
from pyplumio.helpers.typing import DeviceDataType, VersionsInfoType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_FRAME_VERSIONS: Final = "frame_versions"


class FrameVersionsStructure(StructureDecoder):
    """Represents frame version data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        frame_versions: VersionsInfoType = {}
        frame_count = message[offset]
        offset += 1
        for _ in range(frame_count):
            try:
                frame_type = message[offset]
                frame_type = FrameType(frame_type)
            except ValueError:
                pass

            version = util.unpack_ushort(message[offset + 1 : offset + 3])
            frame_versions[frame_type] = version
            offset += 3

        return ensure_device_data(data, {ATTR_FRAME_VERSIONS: frame_versions}), offset
