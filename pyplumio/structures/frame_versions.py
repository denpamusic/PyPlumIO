"""Contains frame versions structure parser."""

from typing import Any, Dict, Tuple

from pyplumio import util
from pyplumio.constants import DATA_FRAMES


def from_bytes(
    message: bytearray, offset: int = 0, data: Dict[str, Any] = None
) -> Tuple[Dict[str, Any], int]:
    """Parses frame message into usable data.

    Keyword arguments:
        message -- message bytes
        offset -- current data offset
    """
    if data is None:
        data = {}

    versions = {}

    frames_number = message[offset]
    offset += 1
    for _ in range(frames_number):
        frame_type = message[offset]
        version = util.unpack_ushort(message[offset + 1 : offset + 3])
        versions[frame_type] = version
        offset += 3

    data[DATA_FRAMES] = versions

    return data, offset
