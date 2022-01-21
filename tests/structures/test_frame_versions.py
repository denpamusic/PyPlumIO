from pyplumio.constants import DATA_FRAMES
from pyplumio.structures import frame_versions

_message = bytearray(
    [
        0x7,
        0x55,
        0x0,
        0x0,
        0x54,
        0x0,
        0x0,
        0x61,
        0x8,
        0x0,
        0x3D,
        0xEC,
        0xF4,
        0x36,
        0x1,
        0x0,
        0x64,
        0x1,
        0x0,
        0x40,
        0x0,
    ]
)
_data = {DATA_FRAMES: {85: 0, 84: 0, 97: 8, 61: 62700, 54: 1, 100: 1, 64: 0}}


def test_from_bytes():
    data, offset = frame_versions.from_bytes(_message)
    assert data == _data
    assert offset == 22
