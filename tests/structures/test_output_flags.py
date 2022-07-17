"""Contains tests for output flags structure."""

from pyplumio.structures.output_flags import (
    CIRCULATION_PUMP_FLAG,
    HEATING_PUMP_FLAG,
    SOLAR_PUMP_FLAG,
    WATER_HEATER_PUMP_FLAG,
    from_bytes,
)

_message = bytearray.fromhex("BF000000")
_data = {
    HEATING_PUMP_FLAG: True,
    WATER_HEATER_PUMP_FLAG: True,
    CIRCULATION_PUMP_FLAG: True,
    SOLAR_PUMP_FLAG: False,
}


def test_from_bytes() -> None:
    """Test conversion from bytes."""
    data, offset = from_bytes(_message)
    assert data == _data
    assert offset == 4
