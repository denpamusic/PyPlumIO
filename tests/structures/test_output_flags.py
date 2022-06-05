"""Test PyPlumIO output flags structure."""

from pyplumio.structures.output_flags import (
    DATA_CIRCULATION_PUMP_FLAG,
    DATA_HEATING_PUMP_FLAG,
    DATA_SOLAR_PUMP_FLAG,
    DATA_WATER_HEATER_PUMP_FLAG,
    from_bytes,
)

_message = bytearray.fromhex("BF000000")
_data = {
    DATA_HEATING_PUMP_FLAG: True,
    DATA_WATER_HEATER_PUMP_FLAG: True,
    DATA_CIRCULATION_PUMP_FLAG: True,
    DATA_SOLAR_PUMP_FLAG: False,
}


def test_from_bytes() -> None:
    """Test conversion from bytes."""
    data, offset = from_bytes(_message)
    assert data == _data
    assert offset == 4
