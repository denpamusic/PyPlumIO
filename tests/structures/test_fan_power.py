"""Contains test for fan power structure decoder."""

import pytest

from pyplumio.frames.messages import SensorDataMessage
from pyplumio.structures.fan_power import ATTR_FAN_POWER, FanPowerStructure


@pytest.fixture(name="fan_power_structure")
def fixture_fan_power_structure() -> FanPowerStructure:
    """Fixture for FanPowerStructure."""
    return FanPowerStructure(frame=SensorDataMessage())


class TestFanPowerStructure:
    """Test the FanPower structure decoder."""

    def test_decode(self, fan_power_structure: FanPowerStructure) -> None:
        """Test decoding of fan power structure."""
        message = bytearray([0x00, 0x00, 0x48, 0x42])
        data, offset = fan_power_structure.decode(message)
        assert data == {ATTR_FAN_POWER: 50.0}
        assert offset == 4

    def test_decode_with_nan(self, fan_power_structure: FanPowerStructure) -> None:
        """Test decoding of fan power structure with NaN value."""
        message = bytearray([0x00, 0x00, 0xC0, 0x7F])  # Represents NaN
        data, offset = fan_power_structure.decode(message)
        assert data == {}
        assert offset == 4
