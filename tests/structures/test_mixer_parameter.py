"""Test PyPlumIO mixer parameter structure."""

from pyplumio.structures import mixer_parameter

_message_zero_parameters = bytearray([0x0, 0x0, 0x0, 0x0])
_message = bytearray(
    [
        0x0,
        0x0,
        0x2,
        0x1,
        0x1E,
        0x28,
        0x3C,
        0x14,
        0x1E,
        0x28,
    ]
)
_data = {"mixers": [{"min_mix_set_temp": (20, 30, 40), "mix_set_temp": (30, 40, 60)}]}


def test_from_bytes_with_zero_parameters():
    """Test conversion from bytes with zero parameters."""
    data, offset = mixer_parameter.from_bytes(_message_zero_parameters)
    assert data == {"mixers": []}
    assert offset == 4


def test_from_bytes():
    """Test conversion from bytes."""
    data, offset = mixer_parameter.from_bytes(_message)
    assert data == _data
    assert offset == 10
