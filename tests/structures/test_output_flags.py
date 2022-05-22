"""Test PyPlumIO output flags structure."""

from pyplumio.constants import (
    DATA_CIRCULATION_PUMP_FLAG,
    DATA_HEATING_PUMP_FLAG,
    DATA_SOLAR_PUMP_FLAG,
    DATA_WATER_HEATER_PUMP_FLAG,
)
from pyplumio.structures import output_flags

_message = bytearray([0xBF, 0x0, 0x0, 0x0])

_data = {
    DATA_HEATING_PUMP_FLAG: True,
    DATA_WATER_HEATER_PUMP_FLAG: True,
    DATA_CIRCULATION_PUMP_FLAG: True,
    DATA_SOLAR_PUMP_FLAG: False,
}


def test_from_bytes() -> None:
    """Test conversion from bytes."""
    data, offset = output_flags.from_bytes(_message)
    assert data == _data
    assert offset == 4
