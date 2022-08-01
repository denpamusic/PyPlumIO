"""Contains frame versions structure decoder."""
from __future__ import annotations

from typing import Optional, Tuple

from pyplumio import util
from pyplumio.const import ATTR_FRAME_VERSIONS
from pyplumio.helpers.typing import DeviceDataType, VersionsInfoType
from pyplumio.structures import StructureDecoder, make_device_data


class FrameVersionsStructure(StructureDecoder):
    """Represents frame version data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        frame_versions: VersionsInfoType = {}
        frames_number = message[offset]
        offset += 1
        for _ in range(frames_number):
            frame_type = message[offset]
            version = util.unpack_ushort(message[offset + 1 : offset + 3])
            frame_versions[frame_type] = version
            offset += 3

        return make_device_data(data, {ATTR_FRAME_VERSIONS: frame_versions}), offset
