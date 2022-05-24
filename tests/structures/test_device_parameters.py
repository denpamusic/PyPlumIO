"""Test PyPlumIO device parameters structure."""

from pyplumio.structures.device_parameters import DEVICE_PARAMETERS, from_bytes

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
    DEVICE_PARAMETERS[0]: (80, 61, 100),
    DEVICE_PARAMETERS[1]: (60, 41, 76),
    DEVICE_PARAMETERS[2]: (40, 20, 59),
    DEVICE_PARAMETERS[4]: (20, 1, 250),
}


def test_from_bytes() -> None:
    """Test conversion from bytes."""
    data, offset = from_bytes(_message)
    assert data == _data
    assert offset == 18


def test_from_bytes_with_no_params() -> None:
    """Test conversion from bytes with no data."""
    data, offset = from_bytes(_message_empty)
    assert not data
    assert offset == 3
