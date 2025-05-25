"""Contains tests for mixer parameters structure decoder."""

import pytest

from pyplumio.frames.responses import MixerParametersResponse
from pyplumio.parameters import ParameterValues
from pyplumio.structures.mixer_parameters import (
    ATTR_MIXER_PARAMETERS,
    MixerParametersStructure,
)


@pytest.fixture(name="mixer_parameters_structure")
def fixture_mixer_parameters_structure() -> MixerParametersStructure:
    """Fixture for MixerParametersStructure."""
    return MixerParametersStructure(frame=MixerParametersResponse())


class TestMixerParametersStructure:
    """Test the MixerParameters structure decoder."""

    def test_decode(self, mixer_parameters_structure: MixerParametersStructure) -> None:
        """Test decoding of mixer parameters structure."""
        message = bytearray([0x01, 0x00, 0x01, 0x01, 0x01, 0x02, 0x03])
        data, offset = mixer_parameters_structure.decode(message)
        assert data == {
            ATTR_MIXER_PARAMETERS: {
                0: [(0, ParameterValues(value=1, min_value=2, max_value=3))]
            }
        }
        assert offset == 7
