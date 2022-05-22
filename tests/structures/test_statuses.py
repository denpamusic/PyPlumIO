"""Test PyPlumIO statuses structure."""

from pyplumio.constants import (
    DATA_HEATING_STATUS,
    DATA_HEATING_TARGET,
    DATA_WATER_HEATER_STATUS,
    DATA_WATER_HEATER_TARGET,
)
from pyplumio.structures import statuses

_message = bytearray([0x32, 0x0, 0x33, 0x0])

_data = {
    DATA_HEATING_TARGET: 50,
    DATA_HEATING_STATUS: 0,
    DATA_WATER_HEATER_TARGET: 51,
    DATA_WATER_HEATER_STATUS: 0,
}


def test_from_bytes() -> None:
    """Test conversion from bytes."""
    data, offset = statuses.from_bytes(_message)
    assert data == _data
    assert offset == 4
