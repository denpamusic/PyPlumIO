"""Test PyPlumIO mixers structure."""

from pyplumio.constants import DATA_MIXERS, MIXER_PUMP, MIXER_TARGET, MIXER_TEMP
from pyplumio.structures import mixers

_message = bytearray(
    [
        0x2,
        0x0,
        0x0,
        0x20,
        0x42,
        0x26,
        0x8,
        0x8,
        0x0,
        0x0,
        0x0,
        0x20,
        0x42,
        0x26,
        0x8,
        0x8,
        0x0,
    ]
)
_data = {
    DATA_MIXERS: [
        {MIXER_TEMP: 40.0, MIXER_TARGET: 38, MIXER_PUMP: False},
        {MIXER_TEMP: 40.0, MIXER_TARGET: 38, MIXER_PUMP: False},
    ]
}


def test_from_bytes() -> None:
    """Test conversion from bytes."""
    data, offset = mixers.from_bytes(_message)
    assert data == _data
    assert offset == 17
