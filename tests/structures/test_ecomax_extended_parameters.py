"""Contains tests for ecoMAX extended parameters structure decoder."""

from typing import Any

import pytest

from pyplumio.frames.responses import EcomaxExtendedParametersResponse
from pyplumio.parameters import ParameterValues
from pyplumio.structures.ecomax_extended_parameters import (
    ATTR_ECOMAX_EXTENDED_PARAMETERS,
    EcomaxExtendedParametersStructure,
)


@pytest.fixture(name="ecomax_extended_parameters_structure")
def fixture_ecomax_extended_parameters_structure() -> EcomaxExtendedParametersStructure:
    """Fixture for EcomaxExtendedParametersStructure."""
    return EcomaxExtendedParametersStructure(frame=EcomaxExtendedParametersResponse())


class TestEcomaxExtendedParametersStructure:
    """Test the EcomaxExtendedParameters structure decoder."""

    def test_decode(
        self, ecomax_extended_parameters_structure: EcomaxExtendedParametersStructure
    ) -> None:
        """Test decoding of ecoMAX extended parameters structure."""
        message = bytes.fromhex("030a020103ffffffff00ff")
        data: dict[str, Any] = {}
        ecomax_extended_parameters_structure.decode(message, data)
        assert data == {
            ATTR_ECOMAX_EXTENDED_PARAMETERS: [
                (10, ParameterValues(value=2, min_value=1, max_value=3)),
                (12, ParameterValues(value=255, min_value=0, max_value=255)),
            ]
        }
        assert ecomax_extended_parameters_structure.offset == 11

    def test_decode_truncated(
        self, ecomax_extended_parameters_structure: EcomaxExtendedParametersStructure
    ) -> None:
        """Test decoding of truncated ecoMAX extended parameters structure."""
        message = bytes.fromhex("e7000501080601")
        data: dict[str, Any] = {}
        ecomax_extended_parameters_structure.decode(message, data)
        assert data == {
            ATTR_ECOMAX_EXTENDED_PARAMETERS: [
                (0, ParameterValues(value=5, min_value=1, max_value=8))
            ]
        }
        assert ecomax_extended_parameters_structure.offset == 5
