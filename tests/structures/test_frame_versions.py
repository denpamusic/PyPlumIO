"""Contains tests for frame versions structure decoder."""

from typing import Any

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
        message = bytes.fromhex("0131FF000000")
        data: dict[str, Any] = {}
        frame_versions_structure.decode(message, data)
        assert data == {ATTR_FRAME_VERSIONS: {FrameType.REQUEST_ECOMAX_PARAMETERS: 255}}
        assert frame_versions_structure.offset == 4
