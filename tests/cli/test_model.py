"""Contains tests for the CLI model module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pyplumio.cli.model import (
    ParameterTable,
    Row,
    load_custom_parameters,
    unpack_parameter_value,
)
from pyplumio.const import STATE_OFF, STATE_ON, UnitOfMeasurement
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.custom import ParameterOverride
from pyplumio.parameters.ecomax import (
    EcomaxNumberDescription,
    EcomaxServiceNumber,
    EcomaxSwitchDescription,
)


@pytest.mark.parametrize(
    ("raw", "step", "offset", "expected"),
    [
        (5, 1, 0, 5),
        (61, 10, 0, 610),
        (8, 0.1, 0, 0.8),
        (20, 0.1, 0, 2.0),
        (25, 1, 20, 5),
        (12, 2.5, 10, 5.0),
        (0, 1.0, 0, 0),
    ],
)
def test_unpack_parameter_value_number(
    raw: int, step: float, offset: int, expected: float | int
) -> None:
    """Test unpack_parameter_value with number descriptions."""
    desc = EcomaxNumberDescription(name="test", step=step, offset=offset)
    result = unpack_parameter_value(raw, desc)
    assert result == expected
    assert type(result) is type(expected)

    # Parity check with EcomaxServiceNumber
    service_num = EcomaxServiceNumber(
        device=MagicMock(),
        description=desc,
        values=ParameterValues(value=raw, min_value=0, max_value=100),
    )
    assert service_num.value == result


def test_unpack_parameter_value_switch() -> None:
    """Test unpack_parameter_value with switch descriptions."""
    desc = EcomaxSwitchDescription(name="switch_test")
    assert unpack_parameter_value(1, desc) == STATE_ON
    assert unpack_parameter_value(0, desc) == STATE_OFF
    assert unpack_parameter_value(42, None) == 42


def test_row_properties() -> None:
    """Test Row properties and formatting."""
    desc = EcomaxNumberDescription(
        name="temp",
        step=1,
        offset=0,
        unit_of_measurement=UnitOfMeasurement.CELSIUS,
    )
    values = ParameterValues(value=20, min_value=10, max_value=30)
    row = Row(index=1, values=values, remaining_updates=5, description=desc)

    assert row.name == "temp"
    assert row.value == 20
    assert row.min_value == 10
    assert row.max_value == 30
    assert bool(row.changed) is True
    assert row.remaining_updates == 5

    row.clear_changed()
    assert bool(row.changed) is False
    assert row.remaining_updates == 0

    row.changed = True
    assert bool(row.changed) is True
    assert row.remaining_updates == 5

    row.changed = False
    assert bool(row.changed) is False
    assert row.remaining_updates == 0

    empty_row = Row(index=2, values=values)
    assert empty_row.name == ""
    assert empty_row.value == 20
    assert empty_row.min_value == 10
    assert empty_row.max_value == 30
    assert bool(empty_row.changed) is False
    assert empty_row.remaining_updates == 0


def test_parameter_table() -> None:
    """Test ParameterTable behavior and update change tracking."""
    desc = EcomaxNumberDescription(name="temp")
    ov = ParameterOverride(original="foo", replacement=desc)
    table = ParameterTable(descriptions={1: desc}, overrides=[ov])

    assert table.descriptions == {1: desc}
    assert table.overrides == (ov,)

    # First update: changed flag should be False for all
    table.update([(1, ParameterValues(value=10, min_value=0, max_value=50))])
    row = table.get(1)
    assert row is not None
    assert bool(row.changed) is False
    assert row.remaining_updates == 0
    assert row.value == 10

    # Second update: same values -> changed is False
    table.update([(1, ParameterValues(value=10, min_value=0, max_value=50))])
    row1 = table.get(1)
    assert row1 is not None and bool(row1.changed) is False
    assert row1.remaining_updates == 0

    # Third update: changed values -> changed is True with 5 intervals
    table.update([(1, ParameterValues(value=15, min_value=0, max_value=50))])
    row1 = table.get(1)
    assert row1 is not None and bool(row1.changed) is True
    assert row1.remaining_updates == 5

    # Check 5 update intervals countdown
    for expected_remaining in (4, 3, 2, 1):
        table.update([(1, ParameterValues(value=15, min_value=0, max_value=50))])
        assert row1.remaining_updates == expected_remaining
        assert bool(row1.changed) is True

    # 5th update without changes -> expires
    table.update([(1, ParameterValues(value=15, min_value=0, max_value=50))])
    assert row1.remaining_updates == 0
    assert bool(row1.changed) is False

    # Check clearing changed state
    table.update([(1, ParameterValues(value=20, min_value=0, max_value=50))])
    assert bool(row1.changed) is True
    assert row1.remaining_updates == 5
    table.clear_changed(1)
    assert bool(row1.changed) is False
    assert row1.remaining_updates == 0

    # Check clearing non-existent row does not error
    table.clear_changed(999)

    # Check rows sorting
    table.update([(0, ParameterValues(value=5, min_value=0, max_value=10))])
    rows = table.rows()
    assert len(rows) == 2
    assert rows[0].index == 0
    assert rows[1].index == 1

    # Check non-existent row
    assert table.get(99) is None

    # Set and remove description
    new_desc = EcomaxSwitchDescription(name="mode")
    table.set_description(0, new_desc)
    assert table.descriptions[0] == new_desc
    row0 = table.get(0)
    assert row0 is not None and row0.description == new_desc

    table.set_description(0, None)
    assert 0 not in table.descriptions
    row0 = table.get(0)
    assert row0 is not None and row0.description is None


def test_load_custom_parameters_from_package() -> None:
    """Test loading custom parameters from installed package."""
    descs, overrides = load_custom_parameters("ecoMAX 350P2-ZF", Path("nonexistent"))
    assert 8 in descs
    assert descs[8].name == "heating_cycle_time"
    assert isinstance(overrides, tuple)


def test_load_custom_parameters_from_output_dir(tmp_path: Path) -> None:
    """Test loading custom parameters from output directory."""
    custom_dir = tmp_path / "pyplumio" / "parameters" / "custom"
    custom_dir.mkdir(parents=True)
    custom_file = custom_dir / "ecomax_dummy.py"
    custom_file.write_text(
        "from pyplumio.parameters.custom import CustomParameters\n"
        "from pyplumio.parameters.ecomax import EcomaxSwitchDescription\n\n"
        "class EcoMAXDUMMY(CustomParameters):\n"
        '    descriptions = {1: EcomaxSwitchDescription(name="dummy_switch")}\n'
        "    overrides = ()\n",
        encoding="utf-8",
    )

    descs, overrides = load_custom_parameters("ecoMAX Dummy", tmp_path)
    assert 1 in descs
    assert descs[1].name == "dummy_switch"
    assert overrides == ()


def test_load_custom_parameters_missing(tmp_path: Path) -> None:
    """Test loading non-existent custom parameters."""
    descs, overrides = load_custom_parameters("ecoMAX Unknown Model", tmp_path)
    assert descs == {}
    assert overrides == ()
