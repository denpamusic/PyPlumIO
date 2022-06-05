"""Test PyPlumIO mixers structure."""

from pyplumio.structures.mixers import (
    DATA_MIXERS,
    MIXER_PUMP,
    MIXER_TARGET,
    MIXER_TEMP,
    from_bytes,
)

_message = bytearray.fromhex("0200002042260808000000204226080800")
_data = {
    DATA_MIXERS: [
        {MIXER_TEMP: 40.0, MIXER_TARGET: 38, MIXER_PUMP: False},
        {MIXER_TEMP: 40.0, MIXER_TARGET: 38, MIXER_PUMP: False},
    ]
}


def test_from_bytes() -> None:
    """Test conversion from bytes."""
    data, offset = from_bytes(_message)
    assert data == _data
    assert offset == 17
