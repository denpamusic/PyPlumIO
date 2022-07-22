"""Contains tests for mixers structure."""

from pyplumio.const import ATTR_MIXER_SENSORS
from pyplumio.structures.mixers import (
    MIXER_PUMP_OUTPUT,
    MIXER_TARGET_TEMP,
    MIXER_TEMP,
    from_bytes,
)

_message = bytearray.fromhex("0200002042260808000000204226080800")
_message_zero_mixers = bytearray.fromhex("00")
_data = {
    ATTR_MIXER_SENSORS: [
        {MIXER_TEMP: 40.0, MIXER_TARGET_TEMP: 38, MIXER_PUMP_OUTPUT: False},
        {MIXER_TEMP: 40.0, MIXER_TARGET_TEMP: 38, MIXER_PUMP_OUTPUT: False},
    ]
}


def test_from_bytes_with_zero_mixers():
    """Test conversion from bytes with zero mixers."""
    data, offset = from_bytes(_message_zero_mixers)
    assert data == {ATTR_MIXER_SENSORS: []}
    assert offset == 1


def test_from_bytes() -> None:
    """Test conversion from bytes."""
    data, offset = from_bytes(_message)
    assert data == _data
    assert offset == 17
