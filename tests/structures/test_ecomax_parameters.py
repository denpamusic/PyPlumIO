"""Contains tests for ecoMAX parameters structure decoder."""

import pytest

from pyplumio.frames.responses import EcomaxParametersResponse
from pyplumio.parameters import ParameterValues
from pyplumio.structures.ecomax_parameters import (
    ATTR_ECOMAX_PARAMETERS,
    EcomaxParametersStructure,
)


@pytest.fixture(name="ecomax_parameters_structure")
def fixture_ecomax_parameters_structure() -> EcomaxParametersStructure:
    """Fixture for EcomaxParametersResponse."""
    return EcomaxParametersStructure(frame=EcomaxParametersResponse())


class TestEcomaxParametersStructure:
    """Test the EcomaxParameters structure decoder."""

    def test_decode(
        self, ecomax_parameters_structure: EcomaxParametersStructure
    ) -> None:
        """Test decoding of ecoMAX parameters structure."""
        message = bytearray([0x01, 0x00, 0x01, 0x02, 0x01, 0x03])
        data, offset = ecomax_parameters_structure.decode(message)
        assert data == {
            ATTR_ECOMAX_PARAMETERS: [
                (0, ParameterValues(value=2, min_value=1, max_value=3))
            ]
        }
        assert offset == 6
