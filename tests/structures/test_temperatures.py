"""Test PyPlumIO temperatures structure."""

from pyplumio.constants import TEMPERATURES
from pyplumio.structures import temperatures

_message = bytearray(
    [
        0x7,
        0x0,
        0xA4,
        0x55,
        0x78,
        0x42,
        0x1,
        0x90,
        0x1B,
        0xCF,
        0x41,
        0x2,
        0x8,
        0xCA,
        0x5F,
        0x42,
        0x3,
        0x0,
        0x90,
        0x7B,
        0xBF,
        0x5,
        0xDF,
        0x9D,
        0x4D,
        0x42,
        0x7,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0x8,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
    ]
)

_data = {
    TEMPERATURES[0]: 62.08363342285156,
    TEMPERATURES[1]: 25.888458251953125,
    TEMPERATURES[2]: 55.947296142578125,
    TEMPERATURES[3]: -0.982666015625,
    TEMPERATURES[5]: 51.404170989990234,
}


def test_from_bytes() -> None:
    """Test conversion from bytes."""
    data, offset = temperatures.from_bytes(_message)
    assert data == _data
    assert offset == 36
