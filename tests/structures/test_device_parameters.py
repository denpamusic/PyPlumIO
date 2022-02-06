from pyplumio.constants import DEVICE_PARAMS
from pyplumio.structures import device_parameters

_message = bytearray(
    [
        0x0,
        0x0,
        0x5,
        0x50,
        0x3D,
        0x64,
        0x3C,
        0x29,
        0x4C,
        0x28,
        0x14,
        0x3B,
        0xFF,
        0xFF,
        0xFF,
        0x14,
        0x01,
        0xFA,
    ]
)
_message_empty = bytearray([0x0, 0x0, 0x0])
_data = {
    DEVICE_PARAMS[0]: (80, 61, 100),
    DEVICE_PARAMS[1]: (60, 41, 76),
    DEVICE_PARAMS[2]: (40, 20, 59),
    DEVICE_PARAMS[4]: (20, 1, 250),
}


def test_from_bytes():
    data, offset = device_parameters.from_bytes(_message)
    assert data == _data
    assert offset == 18


def test_from_bytes_with_no_params():
    data, offset = device_parameters.from_bytes(_message_empty)
    assert not data
    assert offset == 3
