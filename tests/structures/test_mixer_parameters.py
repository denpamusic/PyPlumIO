"""Test PyPlumIO mixer parameter structure."""

from pyplumio.constants import DATA_MIXER_PARAMETERS
from pyplumio.structures.mixer_parameters import from_bytes

_message_zero_parameters = bytearray.fromhex("00000000")
_message = bytearray.fromhex("000002011E283C141E28")
_data = {
    DATA_MIXER_PARAMETERS: [
        {"min_mix_target_temp": (20, 30, 40), "mix_target_temp": (30, 40, 60)}
    ]
}


def test_from_bytes_with_zero_parameters():
    """Test conversion from bytes with zero parameters."""
    data, offset = from_bytes(_message_zero_parameters)
    assert data == {DATA_MIXER_PARAMETERS: []}
    assert offset == 4


def test_from_bytes():
    """Test conversion from bytes."""
    data, offset = from_bytes(_message)
    assert data == _data
    assert offset == 10
