"""Contains tests for ecoMAX service parameters structure decoder."""

from typing import Any

import pytest

from pyplumio.frames.responses import EcomaxServiceParametersResponse
from pyplumio.parameters import ParameterValues
from pyplumio.structures.ecomax_service_parameters import (
    ATTR_ECOMAX_SERVICE_PARAMETERS,
    EcomaxServiceParametersStructure,
)


@pytest.fixture(name="ecomax_service_parameters_structure")
def fixture_ecomax_service_parameters_structure() -> EcomaxServiceParametersStructure:
    """Fixture for EcomaxServiceParametersStructure."""
    return EcomaxServiceParametersStructure(frame=EcomaxServiceParametersResponse())


class TestEcomaxServiceParametersStructure:
    """Test the EcomaxServiceParameters structure decoder."""

    def test_decode(
        self, ecomax_service_parameters_structure: EcomaxServiceParametersStructure
    ) -> None:
        """Test decoding of ecoMAX service parameters structure."""
        message = bytes.fromhex("030a020103ffffffff00ff")
        data: dict[str, Any] = {}
        ecomax_service_parameters_structure.decode(message, data)
        assert data == {
            ATTR_ECOMAX_SERVICE_PARAMETERS: [
                (10, ParameterValues(value=2, min_value=1, max_value=3)),
                (12, ParameterValues(value=255, min_value=0, max_value=255)),
            ]
        }
        assert ecomax_service_parameters_structure.offset == 11

    def test_decode_truncated(
        self, ecomax_service_parameters_structure: EcomaxServiceParametersStructure
    ) -> None:
        """Test decoding of truncated ecoMAX service parameters structure."""
        message = bytes.fromhex("e7000501080601")
        data: dict[str, Any] = {}
        ecomax_service_parameters_structure.decode(message, data)
        assert data == {
            ATTR_ECOMAX_SERVICE_PARAMETERS: [
                (0, ParameterValues(value=5, min_value=1, max_value=8))
            ]
        }
        assert ecomax_service_parameters_structure.offset == 5
