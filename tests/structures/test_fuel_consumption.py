"""Contains tests for fuel consumption structure decoder."""

import pytest

from pyplumio.frames.messages import SensorDataMessage
from pyplumio.structures.fuel_consumption import (
    ATTR_FUEL_CONSUMPTION,
    FuelConsumptionStructure,
)


@pytest.fixture(name="fuel_consumption_structure")
def fixture_fuel_consumption_structure() -> FuelConsumptionStructure:
    """Fixture for FuelConsumptionStructure."""
    return FuelConsumptionStructure(frame=SensorDataMessage())


class TestFuelConsumptionStructure:
    """Test the FuelConsumption structure decoder."""

    def test_decode(self, fuel_consumption_structure: FuelConsumptionStructure) -> None:
        """Test decoding of fuel consumption structure."""
        message = bytearray([0x00, 0x00, 0x48, 0x42])
        data, offset = fuel_consumption_structure.decode(message)
        assert data == {ATTR_FUEL_CONSUMPTION: 50.0}
        assert offset == 4

    def test_decode_with_nan(
        self, fuel_consumption_structure: FuelConsumptionStructure
    ) -> None:
        """Test decoding of fuel consumption structure with NaN value."""
        message = bytearray([0x00, 0x00, 0xC0, 0x7F])  # Represents NaN
        data, offset = fuel_consumption_structure.decode(message)
        assert data == {}
        assert offset == 4
