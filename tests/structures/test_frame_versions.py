"""Contains tests for frame versions structure decoder."""

import pytest

from pyplumio.const import FrameType
from pyplumio.frames.messages import SensorDataMessage
from pyplumio.structures.frame_versions import (
    ATTR_FRAME_VERSIONS,
    FrameVersionsStructure,
)


@pytest.fixture(name="frame_versions_structure")
def fixture_frame_versions_structure() -> FrameVersionsStructure:
    """Fixture for BoilerPowerStructure."""
    return FrameVersionsStructure(frame=SensorDataMessage())


class TestFrameVersionsStructure:
    """Test the FrameVersions structure decoder."""

    def test_decode(self, frame_versions_structure: FrameVersionsStructure) -> None:
        """Test decoding of frame versions structure."""
        message = bytearray([0x01, 0x31, 0xFF, 0x00, 0x00, 0x00])
        data, offset = frame_versions_structure.decode(message)
        assert data == {ATTR_FRAME_VERSIONS: {FrameType.REQUEST_ECOMAX_PARAMETERS: 255}}
        assert offset == 4
