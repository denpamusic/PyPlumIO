"""Contains tests for boiler power structure decoder."""

import pytest

from pyplumio.frames.messages import SensorDataMessage
from pyplumio.structures.boiler_power import ATTR_BOILER_POWER, BoilerPowerStructure


@pytest.fixture(name="boiler_power_structure")
def fixture_boiler_power_structure() -> BoilerPowerStructure:
    """Fixture for BoilerPowerStructure."""
    return BoilerPowerStructure(frame=SensorDataMessage())


class TestBoilerPowerStructure:
    """Test the BoilerPower structure decoder."""

    def test_decode(self, boiler_power_structure: BoilerPowerStructure) -> None:
        """Test decoding of boiler power structure."""
        message = bytearray([0x00, 0x00, 0x48, 0x41])
        data, offset = boiler_power_structure.decode(message)
        assert data == {ATTR_BOILER_POWER: 12.5}
        assert offset == 4

    def test_decode_with_nan(
        self, boiler_power_structure: BoilerPowerStructure
    ) -> None:
        """Test decoding of boiler power structure with NaN value."""
        message = bytearray([0x00, 0x00, 0xC0, 0x7F])  # Represents NaN
        data, offset = boiler_power_structure.decode(message)
        assert data == {}
        assert offset == 4
