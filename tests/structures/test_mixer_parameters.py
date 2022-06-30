"""Contains tests for parameter structure."""

from pyplumio.const import DATA_MIXER_PARAMETERS
from pyplumio.structures.mixer_parameters import from_bytes

_message_zero_parameters = bytearray.fromhex("00000000")
_message = bytearray.fromhex("000002021E1428281E3C2314283C1E3C")
_data = [
    {
        "mix_target_temp": (30, 20, 40),
        "min_mix_target_temp": (40, 30, 60),
    },
    {
        "mix_target_temp": (35, 20, 40),
        "min_mix_target_temp": (60, 30, 60),
    },
]


def test_from_bytes_with_zero_parameters():
    """Test conversion from bytes with zero parameters."""
    data, offset = from_bytes(_message_zero_parameters)
    assert data == {DATA_MIXER_PARAMETERS: []}
    assert offset == 4


def test_from_bytes():
    """Test conversion from bytes."""
    data, offset = from_bytes(_message)
    assert data == {DATA_MIXER_PARAMETERS: _data}
    assert offset == 16
