"""Test boiler load structure decoder."""

import pytest

from pyplumio.const import BYTE_UNDEFINED
from pyplumio.frames.messages import SensorDataMessage
from pyplumio.structures.boiler_load import ATTR_BOILER_LOAD, BoilerLoadStructure


@pytest.fixture(name="boiler_load_structure")
def fixture_boiler_load_structure() -> BoilerLoadStructure:
    """Fixture for AlertsStructure."""
    return BoilerLoadStructure(frame=SensorDataMessage())


class TestBoilerLoadStructure:
    """Test the BoilerLoad structure decoder."""

    def test_decode(self, boiler_load_structure: BoilerLoadStructure) -> None:
        """Test decoding of boiler load structure."""
        message = bytearray([50])
        data, offset = boiler_load_structure.decode(message)
        assert data == {ATTR_BOILER_LOAD: 50}
        assert offset == 1

    def test_decode_without_boiler_load(
        self, boiler_load_structure: BoilerLoadStructure
    ) -> None:
        """Test decoding of boiler load structure without boiler load."""
        message = bytearray([BYTE_UNDEFINED])
        data, offset = boiler_load_structure.decode(message)
        assert data == {}
        assert offset == 1
