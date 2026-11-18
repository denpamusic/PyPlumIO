"""Contains tests for constants."""

from __future__ import annotations

from typing import get_args

from pyplumio.const import PERCENTAGE, UnitOfMeasurement, UnitValue


def test_unit_value_matches_unit_of_measurement() -> None:
    """Test that UnitValue stays in sync with UnitOfMeasurement and PERCENTAGE."""
    expected = {unit.value for unit in UnitOfMeasurement} | {PERCENTAGE}
    unit_values = get_args(UnitValue)
    assert len(unit_values) == len(expected)
    assert set(unit_values) == expected
