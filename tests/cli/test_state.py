"""Contains tests for the CLI state module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from prompt_toolkit.buffer import Buffer

from pyplumio.cli.model import ParameterTable
from pyplumio.cli.session import Session
from pyplumio.cli.state import (
    COMMENT_PROMPT,
    INDEX_PROMPT,
    UNIT_ALIASES,
    AppState,
    AppStep,
    _format_value_with_unit,
    _save_files,
)
from pyplumio.const import PERCENTAGE, ProductType, UnitOfMeasurement
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.ecomax import EcomaxNumberDescription, EcomaxSwitchDescription
from pyplumio.structures.product_info import ProductInfo


def _step(state: AppState) -> AppStep:
    """Return app step without triggering mypy attribute narrowing."""
    return state.step


async def test_app_state_number(tmp_path: Path) -> None:
    """Test AppState navigation and parameter assignment."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    table.update([(0, ParameterValues(value=20, min_value=10, max_value=30))])
    state = AppState(session, table, tmp_path)
    buff = Buffer()
    assert state.prompt == INDEX_PROMPT
    assert state.step == AppStep.INDEX

    # Step 1: Index
    buff.text = "0"
    buff.cursor_position = 1
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.NAME
    assert buff.text == ""
    assert buff.cursor_position == 0
    assert state.data.index == 0

    # Step 2: Name
    buff.text = "boiler_temp"
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.TYPE
    assert state.prompt == "Parameter type (number, switch) [number]: "
    assert state.data.name == "boiler_temp"

    # Step 3: Type default (number)
    buff.text = ""
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.OFFSET

    # Step 4: Offset
    buff.text = "0"
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.STEP
    assert state.data.offset == 0

    # Step 5: Step
    buff.text = "1"
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.UNIT
    assert state.data.step == 1
    assert "Available units:" in state.status

    # Step 6: Unit
    buff.text = "%"
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.COMMENT
    assert state.prompt == COMMENT_PROMPT

    # Step 7: Comment
    buff.text = ""
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.CONFIRM
    assert (
        state.prompt
        == "boiler_temp: 20 % (10-30 %). Does this match your device? [y/N]: "
    )

    # Step 8: Confirm
    buff.text = "y"
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.INDEX
    assert state.prompt == INDEX_PROMPT
    assert state.status == "Stored parameter 0."
    assert 0 in table.descriptions
    desc = table.descriptions[0]
    assert isinstance(desc, EcomaxNumberDescription)
    assert desc.name == "boiler_temp"
    assert desc.unit_of_measurement == PERCENTAGE


async def test_app_state_preview_kw(tmp_path: Path) -> None:
    """Test preview prompt format with kW unit of measurement."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    table.update([(2, ParameterValues(value=16, min_value=11, max_value=16))])
    state = AppState(session, table, tmp_path)
    buff = Buffer()

    buff.text = "2"
    state.dispatch_enter(buff)
    buff.text = "boiler_power"
    state.dispatch_enter(buff)
    buff.text = ""
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.OFFSET
    buff.text = "0"
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.STEP
    buff.text = "1"
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.UNIT
    buff.text = "kW"
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.COMMENT
    buff.text = ""
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.CONFIRM
    assert (
        state.prompt
        == "boiler_power: 16 kW (11-16 kW). Does this match your device? [y/N]: "
    )


async def test_app_state_validation_errors(tmp_path: Path) -> None:
    """Test AppState validation error handling."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    table.update([(0, ParameterValues(value=20, min_value=10, max_value=30))])
    state = AppState(session, table, tmp_path)
    buff = Buffer()

    # Index invalid
    state.dispatch_enter(buff)
    assert state.status == "Index must exist in table."
    assert state.prompt == INDEX_PROMPT

    buff.text = "0"
    state.dispatch_enter(buff)

    # Name invalid
    buff.text = "123_invalid"
    state.dispatch_enter(buff)
    assert "Name must start with a lowercase letter" in state.status

    buff.text = "boiler_temp"
    state.dispatch_enter(buff)

    # Type invalid
    buff.text = "unknown"
    state.dispatch_enter(buff)
    assert "Type must be one of the following: number, switch." in state.status

    buff.text = "number"
    state.dispatch_enter(buff)

    # Offset invalid
    buff.text = "abc"
    state.dispatch_enter(buff)
    assert "Offset must be an integer." in state.status

    buff.text = "0"
    state.dispatch_enter(buff)

    # Step invalid
    buff.text = "-5"
    state.dispatch_enter(buff)
    assert "Step must be a positive number." in state.status

    buff.text = "1"
    state.dispatch_enter(buff)

    # Unit invalid
    buff.text = "invalid_unit"
    state.dispatch_enter(buff)
    assert "Unknown unit of measurement." in state.status


async def test_app_state_name_already_used(tmp_path: Path) -> None:
    """Test rejecting parameter name already used by another index."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    table.update(
        [
            (0, ParameterValues(value=20, min_value=10, max_value=30)),
            (1, ParameterValues(value=50, min_value=0, max_value=100)),
        ]
    )
    table.set_description(1, EcomaxNumberDescription(name="fan_power"))
    state = AppState(session, table, tmp_path)
    buff = Buffer()

    # Selecting index 0 and trying to use "fan_power"
    buff.text = "0"
    state.dispatch_enter(buff)
    buff.text = "fan_power"
    state.dispatch_enter(buff)
    assert state.status == "Name 'fan_power' is already used by index 1."
    assert _step(state) == AppStep.NAME

    # Selecting index 1 and keeping "fan_power" is allowed
    state.reset_app(buff)
    buff.text = "1"
    state.dispatch_enter(buff)
    buff.text = "fan_power"
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.TYPE


async def test_app_state_table_freeze(tmp_path: Path) -> None:
    """Test freezing and unfreezing table rows."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    table.update(
        [
            (0, ParameterValues(value=10, min_value=0, max_value=20)),
            (1, ParameterValues(value=20, min_value=0, max_value=30)),
        ]
    )
    state = AppState(session, table, tmp_path)
    buff = Buffer()

    # Enter editing
    buff.text = "0"
    state.dispatch_enter(buff)

    # Parameter 1 changes while editing index 0: order remains frozen
    table.update([(1, ParameterValues(value=25, min_value=0, max_value=30))])
    assert [row.index for row in table.rows()] == [0, 1]

    # Reset app: table unfreezes
    state.reset_app(buff)
    assert [row.index for row in table.rows()] == [1, 0]


def test_unit_aliases() -> None:
    """Test unit alias mappings."""
    assert UNIT_ALIASES[""] is None
    assert UNIT_ALIASES["none"] is None
    assert UNIT_ALIASES["%"] == PERCENTAGE
    assert UNIT_ALIASES["percent"] == PERCENTAGE
    assert UNIT_ALIASES["percentage"] == PERCENTAGE
    assert UNIT_ALIASES["c"] == UnitOfMeasurement.CELSIUS
    assert UNIT_ALIASES["degc"] == UnitOfMeasurement.CELSIUS
    assert UNIT_ALIASES["d"] == UnitOfMeasurement.DAYS
    assert UNIT_ALIASES["day"] == UnitOfMeasurement.DAYS
    assert UNIT_ALIASES["sec"] == UnitOfMeasurement.SECONDS
    assert UNIT_ALIASES["second"] == UnitOfMeasurement.SECONDS
    assert UNIT_ALIASES["minute"] == UnitOfMeasurement.MINUTES
    assert UNIT_ALIASES["rpm"] == UnitOfMeasurement.REVOLUTIONS_PER_MINUTE
    assert UNIT_ALIASES["kw"] == UnitOfMeasurement.KILO_WATT
    assert UNIT_ALIASES["°c"] == UnitOfMeasurement.CELSIUS
    assert UNIT_ALIASES["celsius"] == UnitOfMeasurement.CELSIUS
    assert "invalid" not in UNIT_ALIASES


async def test_app_state_switch_and_decline(tmp_path: Path) -> None:
    """Test AppState with switch and declining confirm."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    table.update([(1, ParameterValues(value=1, min_value=0, max_value=1))])
    state = AppState(session, table, tmp_path)
    buff = Buffer()

    # Index -> Name -> Type switch -> Confirm -> Decline
    buff.text = "1"
    state.dispatch_enter(buff)
    buff.text = "heating_switch"
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.TYPE
    assert state.prompt == "Parameter type (number, switch) [switch]: "
    buff.text = ""
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.COMMENT
    buff.text = ""
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.CONFIRM
    assert (
        state.prompt
        == "heating_switch: on (off-on). Does this match your device? [y/N]: "
    )

    buff.text = "n"
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.INDEX
    assert state.prompt == INDEX_PROMPT
    assert state.status == "Discarded."
    assert 1 not in table.descriptions


async def test_app_state_type_override(tmp_path: Path) -> None:
    """Test overriding default parameter type suggestion."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    table.update(
        [
            (0, ParameterValues(value=0, min_value=0, max_value=1)),
            (1, ParameterValues(value=20, min_value=10, max_value=30)),
        ]
    )
    state = AppState(session, table, tmp_path)
    buff = Buffer()

    # Switch default overridden with number
    buff.text = "0"
    state.dispatch_enter(buff)
    buff.text = "binary_num"
    state.dispatch_enter(buff)
    assert state.prompt == "Parameter type (number, switch) [switch]: "
    buff.text = "number"
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.OFFSET
    state.reset_app(buff)

    # Number default overridden with switch
    buff.text = "1"
    state.dispatch_enter(buff)
    buff.text = "temp_switch"
    state.dispatch_enter(buff)
    assert state.prompt == "Parameter type (number, switch) [number]: "
    buff.text = "switch"
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.COMMENT
    buff.text = ""
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.CONFIRM


async def test_app_state_index_clears_changed(tmp_path: Path) -> None:
    """Test that selecting an index clears changed state."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    table.update([(0, ParameterValues(value=10, min_value=0, max_value=20))])
    table.update([(0, ParameterValues(value=15, min_value=0, max_value=20))])
    row = table.get(0)
    assert row is not None and bool(row.changed) is True

    state = AppState(session, table, tmp_path)
    buff = Buffer()
    buff.text = "0"
    state.dispatch_enter(buff)
    assert bool(row.changed) is False
    assert row.remaining_updates == 0


async def test_app_state_yes_confirmations(tmp_path: Path) -> None:
    """Test AppState confirming parameter and overwrite with 'yes'."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    table.update([(0, ParameterValues(value=10, min_value=0, max_value=20))])
    state = AppState(session, table, tmp_path)
    buff = Buffer()

    # Confirm with 'yes'
    buff.text = "0"
    state.dispatch_enter(buff)
    buff.text = "test_param"
    state.dispatch_enter(buff)
    buff.text = "number"
    state.dispatch_enter(buff)
    buff.text = "0"
    state.dispatch_enter(buff)
    buff.text = "1"
    state.dispatch_enter(buff)
    buff.text = "none"
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.COMMENT
    buff.text = "# test comment"
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.CONFIRM

    buff.text = "yes"
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.INDEX
    assert state.status == "Stored parameter 0."
    assert table.comments[0] == "test comment"

    # Overwrite with 'yes'
    session.product_info = ProductInfo(
        type=ProductType.ECOMAX_P,
        id=90,
        uid="*TEST*",
        logo=0,
        image=0,
        model="ecoMAX 350P2-ZF",
    )
    session.last_frame_message = b"\x00" * 40
    session.last_parameters = [
        (0, ParameterValues(value=10, min_value=0, max_value=20))
    ]
    state.step_overwrite("yes", buff)
    assert state.status == f"Files saved to {tmp_path}."
    saved_module = (
        tmp_path / "pyplumio" / "parameters" / "custom" / "ecomax_350p2_zf.py"
    ).read_text(encoding="utf-8")
    assert "        # test comment\n" in saved_module


async def test_app_state_save_and_overwrite(tmp_path: Path) -> None:
    """Test saving files via AppState and overwrite flow."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    state = AppState(session, table, tmp_path)
    buff = Buffer()

    # Save before data received
    _save_files(state)
    assert "Error: no data received yet" in state.status

    # Set mock product info, frame data, and mapped description
    session.product_info = ProductInfo(
        type=ProductType.ECOMAX_P,
        id=90,
        uid="*TEST*",
        logo=0,
        image=0,
        model="ecoMAX 350P2-ZF",
    )
    session.last_frame_message = b"\x00" * 40
    session.last_parameters = [
        (0, ParameterValues(value=10, min_value=0, max_value=20))
    ]
    table.set_description(0, EcomaxNumberDescription(name="boiler_temp"))

    _save_files(state)
    assert state.status == f"Files saved to {tmp_path}."

    # Test overwrite declined
    state.step_overwrite("n", buff)
    assert state.status == "Save cancelled."

    # Test overwrite accepted
    state.step_overwrite("y", buff)
    assert state.status == f"Files saved to {tmp_path}."

    # Test error during save
    with patch("pyplumio.cli.state.write_files", side_effect=OSError("Disk full")):
        _save_files(state)
        assert "Error saving files: Disk full" in state.status

    with patch(
        "pyplumio.cli.state.generate_all_files",
        side_effect=ValueError("Invalid parameter"),
    ):
        _save_files(state)
        assert "Error saving files: Invalid parameter" in state.status


def test_format_value_with_unit() -> None:
    """Test formatting values with units of measurement."""
    # Unknown or None description
    assert _format_value_with_unit(10, None) == "10"

    # Number with None unit
    desc_no_unit = EcomaxNumberDescription(name="untyped")
    assert _format_value_with_unit(10, desc_no_unit) == "10"

    # Number with PERCENTAGE constant
    desc_pct = EcomaxNumberDescription(name="fan_power", unit_of_measurement=PERCENTAGE)
    assert _format_value_with_unit(50, desc_pct) == "50 %"

    # Number with "%" literal
    desc_pct_lit = EcomaxNumberDescription(name="fan_power", unit_of_measurement="%")
    assert _format_value_with_unit(100, desc_pct_lit) == "100 %"

    # Number with UnitOfMeasurement
    desc_celsius = EcomaxNumberDescription(
        name="boiler_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
    )
    assert _format_value_with_unit(75.5, desc_celsius) == "75.5 °C"

    desc_kw = EcomaxNumberDescription(
        name="boiler_power", unit_of_measurement=UnitOfMeasurement.KILO_WATT
    )
    assert _format_value_with_unit(16, desc_kw) == "16 kW"

    # Switch description ignores any unit
    switch_desc = EcomaxSwitchDescription(name="heating_pump")
    assert _format_value_with_unit("on", switch_desc) == "on"
    assert _format_value_with_unit("off", switch_desc) == "off"

    # Zero and negative values
    assert _format_value_with_unit(0, desc_pct) == "0 %"
    assert _format_value_with_unit(-10, desc_celsius) == "-10 °C"


async def test_prefilled_defaults_heating_curve_shift(tmp_path: Path) -> None:
    """Test pre-filled defaults when selecting standard number parameter."""
    session = Session(url="socket://localhost:8899")
    session.product_info = ProductInfo(
        type=ProductType.ECOMAX_P,
        id=90,
        uid="*TEST*",
        logo=0,
        image=0,
        model="ecoMAX 350P2-ZF",
    )
    table = ParameterTable()
    table.update([(0, ParameterValues(value=25, min_value=10, max_value=40))])
    state = AppState(session, table, tmp_path)
    buff = Buffer()

    buff.text = "0"
    state.dispatch_enter(buff)
    buff.text = "heating_curve_shift"
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.TYPE
    assert state.prompt == "Parameter type (number, switch) [number]: "

    buff.text = ""
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.OFFSET
    assert state.prompt == "Offset [20]: "

    buff.text = ""
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.STEP
    assert state.prompt == "Step [1]: "

    buff.text = ""
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.UNIT
    assert state.prompt == "Unit [°C]: "

    buff.text = ""
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.COMMENT
    buff.text = ""
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.CONFIRM
    assert (
        state.prompt
        == "heating_curve_shift: 5 °C (-10-20 °C). Does this match your device? [y/N]: "
    )

    buff.text = "y"
    state.dispatch_enter(buff)
    assert table.descriptions[0] == EcomaxNumberDescription(
        name="heating_curve_shift",
        offset=20,
        step=1,
        unit_of_measurement=UnitOfMeasurement.CELSIUS,
    )


async def test_prefilled_defaults_max_fuel_flow_and_unit_override(
    tmp_path: Path,
) -> None:
    """Test decimal step pre-fill and overriding pre-filled unit with none."""
    session = Session(url="socket://localhost:8899")
    session.product_info = ProductInfo(
        type=ProductType.ECOMAX_P,
        id=90,
        uid="*TEST*",
        logo=0,
        image=0,
        model="ecoMAX 350P2-ZF",
    )
    table = ParameterTable()
    table.update(
        [
            (0, ParameterValues(value=10, min_value=0, max_value=50)),
            (1, ParameterValues(value=10, min_value=0, max_value=50)),
        ]
    )
    state = AppState(session, table, tmp_path)
    buff = Buffer()

    # Keep pre-filled 0.2 step and kg/h unit
    buff.text = "0"
    state.dispatch_enter(buff)
    buff.text = "max_fuel_flow"
    state.dispatch_enter(buff)
    buff.text = ""
    state.dispatch_enter(buff)
    assert state.prompt == "Offset [0]: "
    buff.text = ""
    state.dispatch_enter(buff)
    assert state.prompt == "Step [0.2]: "
    buff.text = ""
    state.dispatch_enter(buff)
    assert state.prompt == "Unit [kg/h]: "
    buff.text = ""
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.COMMENT
    buff.text = ""
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.CONFIRM
    buff.text = "y"
    state.dispatch_enter(buff)
    assert table.descriptions[0] == EcomaxNumberDescription(
        name="max_fuel_flow",
        offset=0,
        step=0.2,
        unit_of_measurement=UnitOfMeasurement.KILOGRAMS_PER_HOUR,
    )

    # Override pre-filled unit with "none"
    buff.text = "1"
    state.dispatch_enter(buff)
    buff.text = "fuel_tank_capacity"
    state.dispatch_enter(buff)
    buff.text = ""
    state.dispatch_enter(buff)
    buff.text = ""
    state.dispatch_enter(buff)
    assert state.prompt == "Step [50]: "
    buff.text = ""
    state.dispatch_enter(buff)
    assert state.prompt == "Unit [kg]: "
    buff.text = "none"
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.COMMENT
    buff.text = ""
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.CONFIRM
    buff.text = "y"
    state.dispatch_enter(buff)
    assert table.descriptions[1] == EcomaxNumberDescription(
        name="fuel_tank_capacity",
        offset=0,
        step=50,
        unit_of_measurement=None,
    )


async def test_prefilled_defaults_switch_non_binary(tmp_path: Path) -> None:
    """Test standard switch name gives [switch] default for non-binary raw range."""
    session = Session(url="socket://localhost:8899")
    session.product_info = ProductInfo(
        type=ProductType.ECOMAX_P,
        id=90,
        uid="*TEST*",
        logo=0,
        image=0,
        model="ecoMAX 350P2-ZF",
    )
    table = ParameterTable()
    table.update([(0, ParameterValues(value=1, min_value=0, max_value=10))])
    state = AppState(session, table, tmp_path)
    buff = Buffer()

    buff.text = "0"
    state.dispatch_enter(buff)
    buff.text = "fuzzy_logic"
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.TYPE
    assert state.prompt == "Parameter type (number, switch) [switch]: "

    buff.text = ""
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.COMMENT
    buff.text = ""
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.CONFIRM
    assert state.data.description == EcomaxSwitchDescription(name="fuzzy_logic")
    buff.text = "y"
    state.dispatch_enter(buff)
    assert table.descriptions[0] == EcomaxSwitchDescription(name="fuzzy_logic")


async def test_reedit_mapped_row_preserves_defaults(tmp_path: Path) -> None:
    """Test re-editing mapped row with same name keeps its description values."""
    session = Session(url="socket://localhost:8899")
    session.product_info = ProductInfo(
        type=ProductType.ECOMAX_P,
        id=90,
        uid="*TEST*",
        logo=0,
        image=0,
        model="ecoMAX 350P2-ZF",
    )
    table = ParameterTable()
    table.update(
        [
            (0, ParameterValues(value=25, min_value=10, max_value=40)),
            (1, ParameterValues(value=1, min_value=0, max_value=5)),
        ]
    )
    table.set_description(
        0,
        EcomaxNumberDescription(
            name="heating_curve_shift",
            offset=10,
            step=2,
            unit_of_measurement=UnitOfMeasurement.PASCAL,
        ),
    )
    table.set_description(1, EcomaxSwitchDescription(name="custom_switch"))
    state = AppState(session, table, tmp_path)
    buff = Buffer()

    # Keep existing number name -> preserves custom offset=10, step=2, unit=Pa
    buff.text = "0"
    state.dispatch_enter(buff)
    assert buff.text == "heating_curve_shift"
    assert buff.cursor_position == len("heating_curve_shift")
    for expected_prompt in (
        "Parameter type (number, switch) [number]: ",
        "Offset [10]: ",
        "Step [2]: ",
        "Unit [Pa]: ",
    ):
        state.dispatch_enter(buff)
        assert state.prompt == expected_prompt
        buff.text = ""
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.COMMENT
    buff.text = ""
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.CONFIRM
    buff.text = "y"
    state.dispatch_enter(buff)
    assert table.descriptions[0] == EcomaxNumberDescription(
        name="heating_curve_shift",
        offset=10,
        step=2,
        unit_of_measurement=UnitOfMeasurement.PASCAL,
    )

    # Keep existing switch name -> preserves switch type even when min/max not 0/1
    buff.text = "1"
    state.dispatch_enter(buff)
    assert buff.text == "custom_switch"
    state.dispatch_enter(buff)
    assert state.prompt == "Parameter type (number, switch) [switch]: "


async def test_reedit_mapped_row_switches_on_rename(tmp_path: Path) -> None:
    """Test renaming mapped row switches defaults to new standard or generic."""
    session = Session(url="socket://localhost:8899")
    session.product_info = ProductInfo(
        type=ProductType.ECOMAX_P,
        id=90,
        uid="*TEST*",
        logo=0,
        image=0,
        model="ecoMAX 350P2-ZF",
    )
    table = ParameterTable()
    table.update([(0, ParameterValues(value=25, min_value=10, max_value=40))])
    table.set_description(
        0,
        EcomaxNumberDescription(
            name="heating_curve_shift",
            offset=10,
            step=2,
            unit_of_measurement=UnitOfMeasurement.PASCAL,
        ),
    )
    state = AppState(session, table, tmp_path)
    buff = Buffer()

    # Rename to another standard name -> switches defaults to max_fuel_flow
    buff.text = "0"
    state.dispatch_enter(buff)
    buff.text = "max_fuel_flow"
    for expected_prompt in (
        "Parameter type (number, switch) [number]: ",
        "Offset [0]: ",
        "Step [0.2]: ",
        "Unit [kg/h]: ",
    ):
        state.dispatch_enter(buff)
        assert state.prompt == expected_prompt
        buff.text = ""
    state.reset_app(buff)

    # Rename mapped row to unknown custom name -> resets to generic defaults
    buff.text = "0"
    state.dispatch_enter(buff)
    buff.text = "brand_new_param"
    for expected_prompt in (
        "Parameter type (number, switch) [number]: ",
        "Offset [0]: ",
        "Step [1]: ",
        "Unit [none]: ",
    ):
        state.dispatch_enter(buff)
        assert state.prompt == expected_prompt
        buff.text = ""


async def test_app_state_empty_name_delete_and_cancel(tmp_path: Path) -> None:
    """Test submitting empty name cancels unmapped and deletes mapped parameter."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    table.update([(0, ParameterValues(value=10, min_value=0, max_value=20))])
    state = AppState(session, table, tmp_path)
    buff = Buffer()

    # Unmapped index 0 + empty Name -> resets to INDEX with "Cancelled."
    buff.text = "0"
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.NAME
    buff.text = ""
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.INDEX
    assert state.prompt == INDEX_PROMPT
    assert state.status == "Cancelled."
    assert 0 not in table.descriptions

    # Mapped index 0 (with description and comment) + empty Name -> deletes parameter
    table.set_description(
        0,
        EcomaxNumberDescription(name="boiler_temp"),
        comment="0 - off, 1 - on",
    )
    row0 = table.get(0)
    assert row0 is not None and row0.description is not None

    buff.text = "0"
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.NAME
    assert buff.text == "boiler_temp"
    buff.text = ""
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.INDEX
    assert state.prompt == INDEX_PROMPT
    assert state.status == "Deleted parameter 0."
    assert 0 not in table.descriptions
    assert 0 not in table.comments
    assert row0.description is None


async def test_app_state_comment_reedit_and_clear(tmp_path: Path) -> None:
    """Test comment pre-fill on re-edit and clearing comment on confirmation."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    table.update([(0, ParameterValues(value=1, min_value=0, max_value=1))])
    state = AppState(session, table, tmp_path)
    buff = Buffer()

    # Map index 0 with comment
    buff.text = "0"
    state.dispatch_enter(buff)
    buff.text = "fuel_type"
    state.dispatch_enter(buff)
    buff.text = "switch"
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.COMMENT
    buff.text = "0 - pellets, 1 - wood"
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.CONFIRM
    buff.text = "y"
    state.dispatch_enter(buff)
    assert table.comments[0] == "0 - pellets, 1 - wood"

    # Re-edit index 0 to AppStep.COMMENT: pre-filled with existing comment and keep it
    buff.text = "0"
    state.dispatch_enter(buff)
    state.dispatch_enter(buff)  # keep "fuel_type"
    state.dispatch_enter(buff)  # keep "switch"
    assert _step(state) == AppStep.COMMENT
    assert state.prompt == COMMENT_PROMPT
    assert buff.text == "0 - pellets, 1 - wood"
    assert buff.cursor_position == len("0 - pellets, 1 - wood")
    state.dispatch_enter(buff)  # keep pre-filled comment
    assert _step(state) == AppStep.CONFIRM
    buff.text = "y"
    state.dispatch_enter(buff)
    assert table.comments[0] == "0 - pellets, 1 - wood"

    # Re-edit index 0, clear comment and confirm -> removes comment from table
    buff.text = "0"
    state.dispatch_enter(buff)
    state.dispatch_enter(buff)  # keep "fuel_type"
    state.dispatch_enter(buff)  # keep "switch"
    assert _step(state) == AppStep.COMMENT
    assert buff.text == "0 - pellets, 1 - wood"
    buff.text = ""
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.CONFIRM
    buff.text = "y"
    state.dispatch_enter(buff)
    assert 0 not in table.comments
    assert 0 in table.descriptions
