"""Test PyPlumIO mixers structure."""

from pyplumio.structures.mixers import (
    DATA_MIXERS,
    MIXER_PUMP,
    MIXER_TARGET,
    MIXER_TEMP,
    from_bytes,
)

_message = bytearray.fromhex("0200002042260808000000204226080800")
_message_zero_mixers = bytearray.fromhex("00")
_data = {
    DATA_MIXERS: [
        {MIXER_TEMP: 40.0, MIXER_TARGET: 38, MIXER_PUMP: False},
        {MIXER_TEMP: 40.0, MIXER_TARGET: 38, MIXER_PUMP: False},
    ]
}


def test_from_bytes_with_zero_mixers():
    """Test conversion from bytes with zero mixers."""
    data, offset = from_bytes(_message_zero_mixers)
    assert data == {}
    assert offset == 1


def test_from_bytes() -> None:
    """Test conversion from bytes."""
    data, offset = from_bytes(_message)
    assert data == _data
    assert offset == 17
