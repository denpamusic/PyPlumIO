"""Contains tests for fuel level structure decoder."""

import pytest

from pyplumio.const import BYTE_UNDEFINED
from pyplumio.frames.messages import SensorDataMessage
from pyplumio.structures.fuel_level import ATTR_FUEL_LEVEL, FuelLevelStructure


@pytest.fixture(name="fuel_level_structure")
def fixture_fuel_level_structure() -> FuelLevelStructure:
    """Fixture for FuelLevelStructure."""
    return FuelLevelStructure(frame=SensorDataMessage())


class TestFuelLevelStructure:
    """Test the FuelLevel structure decoder."""

    def test_decode(self, fuel_level_structure: FuelLevelStructure) -> None:
        """Test decoding of fuel level structure."""
        message = bytearray([120])
        data, offset = fuel_level_structure.decode(message)
        assert data == {ATTR_FUEL_LEVEL: 19}
        assert offset == 1

    def test_decode_without_fuel_level(
        self, fuel_level_structure: FuelLevelStructure
    ) -> None:
        """Test decoding of fuel level structure without fuel level."""
        message = bytearray([BYTE_UNDEFINED])
        data, offset = fuel_level_structure.decode(message)
        assert data == {}
        assert offset == 1
