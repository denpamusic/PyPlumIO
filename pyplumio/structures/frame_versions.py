"""Contains frame versions structure parser."""
from __future__ import annotations

from typing import Optional, Tuple

from pyplumio import util
from pyplumio.const import ATTR_FRAME_VERSIONS
from pyplumio.helpers.typing import DeviceDataType, VersionsInfoType


def from_bytes(
    message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
) -> Tuple[DeviceDataType, int]:
    """Parse bytes and return message data and offset."""
    if data is None:
        data = {}

    versions: VersionsInfoType = {}
    frames_number = message[offset]
    offset += 1
    for _ in range(frames_number):
        frame_type = message[offset]
        version = util.unpack_ushort(message[offset + 1 : offset + 3])
        versions[frame_type] = version
        offset += 3

    data[ATTR_FRAME_VERSIONS] = versions

    return data, offset
