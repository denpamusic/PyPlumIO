"""Test PyPlumIO statuses structure."""

from pyplumio.structures.statuses import (
    HEATING_STATUS,
    HEATING_TARGET,
    WATER_HEATER_STATUS,
    WATER_HEATER_TARGET,
    from_bytes,
)

_message = bytearray.fromhex("32003300")
_data = {
    HEATING_TARGET: 50,
    HEATING_STATUS: 0,
    WATER_HEATER_TARGET: 51,
    WATER_HEATER_STATUS: 0,
}


def test_from_bytes() -> None:
    """Test conversion from bytes."""
    data, offset = from_bytes(_message)
    assert data == _data
    assert offset == 4
