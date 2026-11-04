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
    assert empty_row.change_order == 0


def test_parameter_table() -> None:
    """Test ParameterTable basic behavior and descriptions."""
    desc = EcomaxNumberDescription(name="temp")
    ov = ParameterOverride(original="foo", replacement=desc)
    table = ParameterTable(descriptions={1: desc}, overrides=[ov])

    assert table.descriptions == {1: desc}
    assert table.overrides == (ov,)
    assert len(table) == 0
    assert table.rows() == []

    # First update: changed flag should be False for all
    table.update([(1, ParameterValues(value=10, min_value=0, max_value=50))])
    assert len(table) == 1
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

    # Check clearing changed state
    table.clear_changed(1)
    assert bool(row1.changed) is False
    assert row1.remaining_updates == 0

    # Check clearing non-existent row does not error
    table.clear_changed(999)

    # Check rows sorting: row 1 was changed, so stays stacked at the top
    table.update([(0, ParameterValues(value=5, min_value=0, max_value=10))])
    rows = table.rows()
    assert len(rows) == 2
    assert rows[0].index == 1
    assert rows[1].index == 0

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


def test_parameter_table_change_countdown() -> None:
    """Test ParameterTable 5-interval countdown and reset on re-change."""
    table = ParameterTable()
    table.update([(1, ParameterValues(value=10, min_value=0, max_value=50))])
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

    # Check that a new change resets countdown back to 5
    table.update([(1, ParameterValues(value=20, min_value=0, max_value=50))])
    assert bool(row1.changed) is True
    assert row1.remaining_updates == 5
    table.update([(1, ParameterValues(value=20, min_value=0, max_value=50))])
    assert row1.remaining_updates == 4
    # Change again before expiry: resets to 5
    table.update([(1, ParameterValues(value=25, min_value=0, max_value=50))])
    assert row1.remaining_updates == 5


def test_parameter_table_multi_row_updates() -> None:
    """Test ParameterTable multi-row updates and independent countdowns."""
    table = ParameterTable()
    table.update(
        [
            (0, ParameterValues(value=5, min_value=0, max_value=10)),
            (1, ParameterValues(value=20, min_value=0, max_value=50)),
        ]
    )
    row0 = table.get(0)
    row1 = table.get(1)
    assert row0 is not None and row1 is not None
    assert bool(row0.changed) is False
    assert bool(row1.changed) is False

    # Both change
    table.update(
        [
            (0, ParameterValues(value=6, min_value=0, max_value=10)),
            (1, ParameterValues(value=25, min_value=0, max_value=50)),
        ]
    )
    assert bool(row0.changed) is True and row0.remaining_updates == 5
    assert bool(row1.changed) is True and row1.remaining_updates == 5

    # Row 0 unchanged (counts down to 4), row 1 changes again (resets to 5)
    table.update(
        [
            (0, ParameterValues(value=6, min_value=0, max_value=10)),
            (1, ParameterValues(value=30, min_value=0, max_value=50)),
        ]
    )
    assert row0.remaining_updates == 4
    assert row1.remaining_updates == 5


def test_parameter_table_rows_stack_sorting() -> None:
    """Test ParameterTable rows sorting in stack order on updates."""
    table = ParameterTable()
    # Initial load of 5 parameters: all unchanged, sorted by index ascending
    table.update(
        [
            (i, ParameterValues(value=10 * i, min_value=0, max_value=100))
            for i in range(5)
        ]
    )
    assert [row.index for row in table.rows()] == [0, 1, 2, 3, 4]

    # Parameter 3 changes -> pushed to top of stack
    table.update([(3, ParameterValues(value=35, min_value=0, max_value=100))])
    assert [row.index for row in table.rows()] == [3, 0, 1, 2, 4]
    row3 = table.get(3)
    assert row3 is not None
    assert bool(row3.changed) is True

    # Parameter 1 changes -> pushed to top of stack (above 3)
    table.update([(1, ParameterValues(value=15, min_value=0, max_value=100))])
    assert [row.index for row in table.rows()] == [1, 3, 0, 2, 4]
    row1 = table.get(1)
    assert row1 is not None
    assert bool(row1.changed) is True

    # Parameters 0 and 4 change in the same update -> pushed to top, ordered by index
    table.update(
        [
            (0, ParameterValues(value=5, min_value=0, max_value=100)),
            (4, ParameterValues(value=45, min_value=0, max_value=100)),
        ]
    )
    assert [row.index for row in table.rows()] == [0, 4, 1, 3, 2]

    # 5 update intervals pass without changes -> highlights expire,
    # but stack order is preserved
    for _ in range(5):
        table.update([])
    assert [row.index for row in table.rows()] == [0, 4, 1, 3, 2]
    assert all(not row.changed for row in table.rows())

    # Parameter 3 changes again -> moves back to the very top of stack
    table.update([(3, ParameterValues(value=38, min_value=0, max_value=100))])
    assert [row.index for row in table.rows()] == [3, 0, 4, 1, 2]

    # Clearing changed state does not reset stack position
    table.clear_changed(3)
    row3_cleared = table.get(3)
    assert row3_cleared is not None
    assert bool(row3_cleared.changed) is False
    assert [row.index for row in table.rows()] == [3, 0, 4, 1, 2]

    # Newly discovered parameter 5 arrives -> stays with unchanged parameters
    table.update([(5, ParameterValues(value=50, min_value=0, max_value=100))])
    assert [row.index for row in table.rows()] == [3, 0, 4, 1, 2, 5]

    # Parameter 1 changes again -> moves above 3 to the very top
    table.update([(1, ParameterValues(value=18, min_value=0, max_value=100))])
    assert [row.index for row in table.rows()] == [1, 3, 0, 4, 2, 5]


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
