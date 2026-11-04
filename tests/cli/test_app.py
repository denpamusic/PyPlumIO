"""Contains tests for the CLI app module."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from prompt_toolkit.application import create_app_session
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import OneStyleAndTextTuple
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.key_binding import KeyPressEvent
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.shortcuts import PromptSession
from prompt_toolkit.validation import ValidationError
import pytest

from pyplumio.cli.app import (
    INDEX_PROMPT,
    PREVIEW_BOX_WIDTH,
    AppState,
    _get_header_text,
    _get_preview_text,
    _get_table_text,
    _parse_unit,
    _save_files,
    create_app,
    prompt_connection_url,
    run_app,
)
from pyplumio.cli.model import ParameterTable
from pyplumio.cli.session import Session
from pyplumio.const import PERCENTAGE, ProductType, UnitOfMeasurement
from pyplumio.exceptions import PyPlumIOError
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.ecomax import EcomaxNumberDescription, EcomaxSwitchDescription
from pyplumio.structures.product_info import ProductInfo


async def test_prompt_connection_url_tcp() -> None:
    """Test prompting for TCP connection URL."""
    mock_session = MagicMock(spec=PromptSession)
    mock_session.prompt_async = AsyncMock(side_effect=["tcp", "192.168.1.50", "8899"])

    url = await prompt_connection_url(mock_session)
    assert url == "socket://192.168.1.50:8899"

    # Verify validators passed
    calls = mock_session.prompt_async.call_args_list
    type_validator = calls[0].kwargs["validator"]
    type_validator.validate(Document("tcp"))
    type_validator.validate(Document("SERIAL"))
    with pytest.raises(ValidationError):
        type_validator.validate(Document("invalid"))

    host_validator = calls[1].kwargs["validator"]
    host_validator.validate(Document("localhost"))
    with pytest.raises(ValidationError):
        host_validator.validate(Document(""))

    port_validator = calls[2].kwargs["validator"]
    port_validator.validate(Document("8899"))
    port_validator.validate(Document(""))
    with pytest.raises(ValidationError):
        port_validator.validate(Document("0"))
    with pytest.raises(ValidationError):
        port_validator.validate(Document("70000"))
    with pytest.raises(ValidationError):
        port_validator.validate(Document("abc"))


async def test_prompt_connection_url_tcp_default_port() -> None:
    """Test prompting for TCP connection URL with default port."""
    mock_session = MagicMock(spec=PromptSession)
    mock_session.prompt_async = AsyncMock(side_effect=["tcp", "localhost", ""])

    url = await prompt_connection_url(mock_session)
    assert url == "socket://localhost:8899"


async def test_prompt_connection_url_serial() -> None:
    """Test prompting for serial connection URL."""
    mock_session = MagicMock(spec=PromptSession)
    mock_session.prompt_async = AsyncMock(side_effect=["serial", "COM3"])

    url = await prompt_connection_url(mock_session)
    assert url == "COM3"

    url_validator = mock_session.prompt_async.call_args_list[1].kwargs["validator"]
    url_validator.validate(Document("/dev/ttyUSB0"))
    with pytest.raises(ValidationError):
        url_validator.validate(Document(""))


async def test_app_state_wizard_number(tmp_path: Path) -> None:
    """Test AppState wizard navigation and parameter assignment."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    table.update([(0, ParameterValues(value=20, min_value=10, max_value=30))])
    state = AppState(session, table, tmp_path)
    buff = Buffer()
    assert state.prompt == INDEX_PROMPT

    # Step 1: Index
    buff.text = "0"
    state.dispatch_enter(buff)
    assert state.state == "NAME"
    assert state.wizard_data["index"] == 0

    # Step 2: Name
    buff.text = "boiler_temp"
    state.dispatch_enter(buff)
    assert state.state == "TYPE"
    assert state.prompt == "Parameter type (number, switch) [number]: "
    assert state.wizard_data["name"] == "boiler_temp"

    # Step 3: Type default (number)
    buff.text = ""
    state.dispatch_enter(buff)
    assert state.state == "OFFSET"

    # Step 4: Offset
    buff.text = "0"
    state.dispatch_enter(buff)
    assert state.state == "STEP"
    assert state.wizard_data["offset"] == 0

    # Step 5: Step
    buff.text = "1"
    state.dispatch_enter(buff)
    assert state.state == "UNIT"
    assert state.wizard_data["step"] == 1
    assert "Available units:" in state.status

    # Step 6: Unit
    buff.text = "%"
    state.dispatch_enter(buff)
    assert state.state == "CONFIRM"
    assert (
        state.prompt
        == "boiler_temp: 20% (10-30%). Does this match your device? [y/N]: "
    )

    # Step 7: Confirm
    buff.text = "y"
    state.dispatch_enter(buff)
    assert state.state == "INDEX"
    assert state.prompt == INDEX_PROMPT
    assert state.status == "Stored parameter 0."
    assert 0 in table.descriptions
    desc = table.descriptions[0]
    assert isinstance(desc, EcomaxNumberDescription)
    assert desc.name == "boiler_temp"
    assert desc.unit_of_measurement == PERCENTAGE


async def test_app_state_wizard_preview_kw(tmp_path: Path) -> None:
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
    buff.text = ""  # Default to number
    state.dispatch_enter(buff)
    assert state.state == "OFFSET"
    buff.text = "0"
    state.dispatch_enter(buff)
    assert state.state == "STEP"
    buff.text = "1"
    state.dispatch_enter(buff)
    assert state.state == "UNIT"
    buff.text = "kW"
    state.dispatch_enter(buff)
    assert state.state == "CONFIRM"
    assert (
        state.prompt
        == "boiler_power: 16 kW (11-16 kW). Does this match your device? [y/N]: "
    )


async def test_app_state_wizard_validation_errors(tmp_path: Path) -> None:
    """Test AppState wizard validation error handling."""
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
    assert "Type must be 'number' or 'switch'." in state.status

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


def test_parse_unit() -> None:
    """Test parsing of unit strings."""
    assert _parse_unit("") is None
    assert _parse_unit("none") is None
    assert _parse_unit("None") is None
    assert _parse_unit("%") == PERCENTAGE
    assert _parse_unit("percent") == PERCENTAGE
    assert _parse_unit("percentage") == PERCENTAGE
    assert _parse_unit("c") == UnitOfMeasurement.CELSIUS
    assert _parse_unit("degc") == UnitOfMeasurement.CELSIUS
    assert _parse_unit("d") == UnitOfMeasurement.DAYS
    assert _parse_unit("day") == UnitOfMeasurement.DAYS
    assert _parse_unit("sec") == UnitOfMeasurement.SECONDS
    assert _parse_unit("second") == UnitOfMeasurement.SECONDS
    assert _parse_unit("minute") == UnitOfMeasurement.MINUTES
    assert _parse_unit("rpm") == UnitOfMeasurement.REVOLUTIONS_PER_MINUTE
    assert _parse_unit("RPM") == UnitOfMeasurement.REVOLUTIONS_PER_MINUTE
    assert _parse_unit("kw") == UnitOfMeasurement.KILO_WATT
    assert _parse_unit("kW") == UnitOfMeasurement.KILO_WATT
    assert _parse_unit("°c") == UnitOfMeasurement.CELSIUS
    assert _parse_unit("CELSIUS") == UnitOfMeasurement.CELSIUS
    assert _parse_unit("  kW  ") == UnitOfMeasurement.KILO_WATT
    assert _parse_unit("invalid") is False


async def test_app_state_switch_and_decline(tmp_path: Path) -> None:
    """Test AppState wizard with switch and declining confirm."""
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
    assert state.state == "TYPE"
    assert state.prompt == "Parameter type (number, switch) [switch]: "
    buff.text = ""  # Default to switch
    state.dispatch_enter(buff)
    assert state.state == "CONFIRM"
    assert (
        state.prompt
        == "heating_switch: on (off-on). Does this match your device? [y/N]: "
    )

    buff.text = "n"
    state.dispatch_enter(buff)
    assert state.state == "INDEX"
    assert state.prompt == INDEX_PROMPT
    assert state.status == "Discarded."
    assert 1 not in table.descriptions


async def test_app_state_wizard_type_override(tmp_path: Path) -> None:
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
    assert state.state == "OFFSET"
    state.reset_wizard(buff)

    # Number default overridden with switch
    buff.text = "1"
    state.dispatch_enter(buff)
    buff.text = "temp_switch"
    state.dispatch_enter(buff)
    assert state.prompt == "Parameter type (number, switch) [number]: "
    buff.text = "switch"
    state.dispatch_enter(buff)
    assert state.state == "CONFIRM"


async def test_app_state_index_clears_changed(tmp_path: Path) -> None:
    """Test that selecting an index in the wizard clears changed state."""
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
    """Test AppState wizard confirming parameter and overwrite with 'yes'."""
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
    assert state.state == "CONFIRM"

    buff.text = "yes"
    state.dispatch_enter(buff)
    assert state.state == "INDEX"
    assert state.status == "Stored parameter 0."

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


async def test_app_state_save_and_overwrite(tmp_path: Path) -> None:
    """Test saving files via AppState and overwrite flow."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    state = AppState(session, table, tmp_path)
    buff = Buffer()

    # Save before data received
    _save_files(state)
    assert "Error: no data received yet" in state.status

    # Set mock product info and frame data
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

    _save_files(state)
    assert state.status == f"Files saved to {tmp_path}."

    # Test overwrite declined
    state.step_overwrite("n", buff)
    assert state.status == "Save cancelled."

    # Test overwrite accepted
    state.step_overwrite("y", buff)
    assert state.status == f"Files saved to {tmp_path}."

    # Test error during save
    with patch("pyplumio.cli.app.write_files", side_effect=OSError("Disk full")):
        _save_files(state)
        assert "Error saving files: Disk full" in state.status


def test_ui_header_and_table_text(tmp_path: Path) -> None:
    """Test header and table formatting functions."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    state = AppState(session, table, tmp_path)

    # Initial header without product info or update time
    header = _get_header_text(state)
    assert "Model: Unknown (ID: 0)" in header[0][1]
    assert "Updated: Never" in header[0][1]

    # Header with product info and update time
    session.product_info = ProductInfo(
        type=ProductType.ECOMAX_P,
        id=90,
        uid="*TEST*",
        logo=0,
        image=0,
        model="ecoMAX 350P2-ZF",
    )
    session.last_update_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    header = _get_header_text(state)
    assert "Model: ecoMAX 350P2-ZF (ID: 90)" in header[0][1]
    assert "Updated: 12:00:00" in header[0][1]

    # Table text
    table.update([(0, ParameterValues(value=10, min_value=0, max_value=20))])
    lines = _get_table_text(state)
    assert len(lines) >= 3
    assert lines[2][0] == ""
    assert "10" in lines[2][1]

    table.update([(0, ParameterValues(value=15, min_value=0, max_value=20))])
    lines = _get_table_text(state)
    assert len(lines) >= 3
    assert lines[2][0] == "reverse"
    assert "15" in lines[2][1]
    assert "*" not in lines[2][1]


def test_live_preview_box_index(tmp_path: Path) -> None:
    """Test live preview box in INDEX state."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    table.update(
        [
            (0, ParameterValues(value=20, min_value=10, max_value=30)),
            (1, ParameterValues(value=1, min_value=0, max_value=1)),
        ]
    )
    state = AppState(session, table, tmp_path)
    buff = Buffer()

    # 1. INDEX state - empty buffer (shows placeholder box)
    buff.text = ""
    lines = _get_preview_text(state, buff)
    assert len(lines) == 1
    content = lines[0][1]
    assert "┌─ Live Preview" in content
    assert "Enter a parameter index below to preview raw values" in content
    assert len(content.splitlines()) == 4
    assert all(len(line) == PREVIEW_BOX_WIDTH for line in content.splitlines())

    # 1b. INDEX state - non-digit or non-existent index (shows placeholder box)
    buff.text = "abc"
    assert "Enter a parameter index below" in _get_preview_text(state, buff)[0][1]
    buff.text = "99"
    assert "Enter a parameter index below" in _get_preview_text(state, buff)[0][1]

    # 1c. INDEX state - existing index typed before enter
    buff.text = "0"
    content = _get_preview_text(state, buff)[0][1]
    assert "Live Preview (Index #0)" in content
    assert "Name: <unnamed>" in content
    assert "Type: number" in content
    assert "Offset: 0" in content
    assert "Step: 1" in content
    assert "Unit: none" in content
    assert "Raw: 20 (min: 10, max: 30)  ──►  Preview: 20 (10-30)" in content
    assert len(content.splitlines()) == 4
    assert all(len(line) == PREVIEW_BOX_WIDTH for line in content.splitlines())

    # 1d. INDEX state - index with existing description
    table.set_description(
        0,
        EcomaxNumberDescription(
            name="existing_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
    )
    content = _get_preview_text(state, buff)[0][1]
    assert "Name: existing_temp" in content
    assert "Unit: °C" in content
    assert "Preview: 20 °C (10-30 °C)" in content


def test_live_preview_box_name(tmp_path: Path) -> None:
    """Test live preview box in NAME state."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    table.update(
        [
            (0, ParameterValues(value=20, min_value=10, max_value=30)),
            (1, ParameterValues(value=1, min_value=0, max_value=1)),
        ]
    )
    state = AppState(session, table, tmp_path)
    buff = Buffer()

    # 2. NAME state
    buff.text = "0"
    state.dispatch_enter(buff)
    assert state.state == "NAME"
    buff.text = ""
    content = _get_preview_text(state, buff)[0][1]
    assert "[Name: <unnamed>]" in content

    buff.text = "boiler_power"
    content = _get_preview_text(state, buff)[0][1]
    assert "[Name: boiler_power]" in content
    assert "Type: number" in content

    # 2b. NAME state with switch row
    state.reset_wizard(buff)
    table.set_description(1, EcomaxSwitchDescription(name="old_switch"))
    buff.text = "1"
    state.dispatch_enter(buff)
    buff.text = "heating_switch"
    content = _get_preview_text(state, buff)[0][1]
    assert "[Name: heating_switch]" in content
    assert "Type: switch" in content
    assert "Offset" not in content


def test_live_preview_box_type_offset_step(tmp_path: Path) -> None:
    """Test live preview box through type, offset, and step states."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    table.update([(0, ParameterValues(value=20, min_value=10, max_value=30))])
    state = AppState(session, table, tmp_path)
    buff = Buffer()

    # Enter wizard and advance to TYPE
    buff.text = "0"
    state.dispatch_enter(buff)
    buff.text = "boiler_power"
    state.dispatch_enter(buff)
    assert state.state == "TYPE"

    # Default type (number) when text is empty
    buff.text = ""
    content = _get_preview_text(state, buff)[0][1]
    assert "[Type: number]" in content
    assert "Offset: 0" in content

    # Preview as switch
    buff.text = "switch"
    content = _get_preview_text(state, buff)[0][1]
    assert "[Type: switch]" in content
    assert "Offset" not in content
    assert "Preview: off (off-on)" in content

    # Advance to OFFSET state
    buff.text = "number"
    state.dispatch_enter(buff)
    assert state.state == "OFFSET"

    buff.text = ""
    assert "[Offset: 0]" in _get_preview_text(state, buff)[0][1]
    buff.text = "-50"
    content = _get_preview_text(state, buff)[0][1]
    assert "[Offset: -50]" in content
    assert "Preview: 70 (60-80)" in content
    buff.text = "abc"
    assert "[Offset: 0]" in _get_preview_text(state, buff)[0][1]

    # Advance to STEP state
    buff.text = "5"
    state.dispatch_enter(buff)
    assert state.state == "STEP"
    assert state.wizard_data["offset"] == 5

    buff.text = ""
    assert "[Step: 1]" in _get_preview_text(state, buff)[0][1]
    buff.text = "0.1"
    content = _get_preview_text(state, buff)[0][1]
    assert "[Step: 0.1]" in content
    assert "Preview: 1.5 (0.5-2.5)" in content
    buff.text = "10"
    content = _get_preview_text(state, buff)[0][1]
    assert "[Step: 10]" in content
    assert "Preview: 150 (50-250)" in content
    buff.text = "-1"
    assert "[Step: 1]" in _get_preview_text(state, buff)[0][1]
    buff.text = "abc"
    assert "[Step: 1]" in _get_preview_text(state, buff)[0][1]


def test_live_preview_box_unit_confirm_overwrite(tmp_path: Path) -> None:
    """Test live preview box through unit, confirm, and overwrite states."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    table.update([(0, ParameterValues(value=20, min_value=10, max_value=30))])
    state = AppState(session, table, tmp_path)
    state.wizard_data.update(
        {"index": 0, "name": "boiler_power", "offset": 5, "step": 0.5}
    )
    state.state = "UNIT"
    buff = Buffer()

    buff.text = ""
    content = _get_preview_text(state, buff)[0][1]
    assert "[Unit: none]" in content
    assert "Preview: 7.5 (2.5-12.5)" in content
    buff.text = "kW"
    content = _get_preview_text(state, buff)[0][1]
    assert "[Unit: kW]" in content
    assert "Preview: 7.5 kW (2.5-12.5 kW)" in content
    buff.text = "%"
    content = _get_preview_text(state, buff)[0][1]
    assert "[Unit: %]" in content
    assert "Preview: 7.5% (2.5-12.5%)" in content
    buff.text = "invalid_unit"
    assert "[Unit: none]" in _get_preview_text(state, buff)[0][1]

    # Advance to CONFIRM state
    buff.text = "°C"
    state.dispatch_enter(buff)
    assert state.state == "CONFIRM"
    content = _get_preview_text(state, buff)[0][1]
    assert "Name: boiler_power" in content
    assert "Type: number" in content
    assert "Offset: 5" in content
    assert "Step: 0.5" in content
    assert "Unit: °C" in content
    assert "Preview: 7.5 °C (2.5-12.5 °C)" in content

    # OVERWRITE state
    state.state = "OVERWRITE"
    assert "Live Preview (Index #0)" in _get_preview_text(state, buff)[0][1]

    # Parameter with exceptionally long name clamps to PREVIEW_BOX_WIDTH
    state.wizard_data["name"] = "a" * 80
    long_content = _get_preview_text(state, buff)[0][1]
    assert len(long_content.splitlines()) == 4
    assert all(len(line) == PREVIEW_BOX_WIDTH for line in long_content.splitlines())


def _assert_table_row(line: OneStyleAndTextTuple, index: int, style: str) -> None:
    """Assert formatted table row index and style."""
    assert f"    {index}  " in line[1]
    assert line[0] == style


def test_table_text_stack_order(tmp_path: Path) -> None:
    """Test table text ordering reflects stack order of changes."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    state = AppState(session, table, tmp_path)

    # Initial update with three parameters: ordered by index
    table.update(
        [
            (0, ParameterValues(value=10, min_value=0, max_value=20)),
            (1, ParameterValues(value=20, min_value=0, max_value=30)),
            (2, ParameterValues(value=30, min_value=0, max_value=40)),
        ]
    )
    lines = _get_table_text(state)
    _assert_table_row(lines[2], 0, "")
    _assert_table_row(lines[3], 1, "")
    _assert_table_row(lines[4], 2, "")

    # Parameter 2 changes: pushed to top with reverse style
    table.update([(2, ParameterValues(value=35, min_value=0, max_value=40))])
    lines = _get_table_text(state)
    _assert_table_row(lines[2], 2, "reverse")
    _assert_table_row(lines[3], 0, "")
    _assert_table_row(lines[4], 1, "")

    # Parameter 1 changes: pushed above parameter 2
    table.update([(1, ParameterValues(value=25, min_value=0, max_value=30))])
    lines = _get_table_text(state)
    _assert_table_row(lines[2], 1, "reverse")
    _assert_table_row(lines[3], 2, "reverse")
    _assert_table_row(lines[4], 0, "")

    # Clear changed on parameter 1 via wizard selection:
    # stays at top, reverse style removed
    buff = Buffer()
    buff.text = "1"
    state.dispatch_enter(buff)
    lines = _get_table_text(state)
    _assert_table_row(lines[2], 1, "")
    _assert_table_row(lines[3], 2, "reverse")
    _assert_table_row(lines[4], 0, "")

    # Parameter 2 changes again: moves back above parameter 1
    table.update([(2, ParameterValues(value=38, min_value=0, max_value=40))])
    lines = _get_table_text(state)
    _assert_table_row(lines[2], 2, "reverse")
    _assert_table_row(lines[3], 1, "")
    _assert_table_row(lines[4], 0, "")

    # After 5 intervals without changes: reverse style expires, stack order holds
    for _ in range(5):
        table.update([])
    lines = _get_table_text(state)
    _assert_table_row(lines[2], 2, "")
    _assert_table_row(lines[3], 1, "")
    _assert_table_row(lines[4], 0, "")


def test_app_keybindings_and_layout(tmp_path: Path) -> None:
    """Test registered keybindings and application layout."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    app = create_app(session, table, tmp_path, output=DummyOutput())

    assert app.key_bindings is not None
    bindings = {b.keys[0]: b.handler for b in app.key_bindings.bindings}
    mock_event = MagicMock(spec=KeyPressEvent)
    mock_event.app = MagicMock()

    # 1. c-q
    bindings["c-q"](mock_event)
    mock_event.app.exit.assert_called_once()

    # 2. c-s without product info
    bindings["c-s"](mock_event)
    state = getattr(app, "state")
    assert state.status == "No connection or product info yet."

    # 2b. c-s with product info and no file
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
    bindings["c-s"](mock_event)
    assert state.status == f"Files saved to {tmp_path}."

    # 2c. c-s with product info and existing file
    bindings["c-s"](mock_event)
    assert state.state == "OVERWRITE"
    assert (
        state.prompt
        == "Overwrite existing ecomax_350p2_zf.py? Comments will be lost [y/N]: "
    )
    assert str(tmp_path) not in state.prompt

    # 3. escape
    bindings["escape"](mock_event)
    assert state.state == "INDEX"
    assert state.status == "Cancelled."

    # 4. live preview container check
    preview_win = app.layout.container.content.children[3]  # type: ignore[attr-defined]
    assert preview_win.height == 4
    preview_output = preview_win.content.text()
    assert "Live Preview" in preview_output[0][1]

    # 5. completer checks
    buffer_ctrl = app.layout.container.content.children[5].children[1]  # type: ignore[attr-defined]
    app_buffer = buffer_ctrl.content.buffer
    assert app_buffer.completer is not None
    assert list(app_buffer.completer.get_completions(Document(""), None)) == []
    state.state = "TYPE"
    assert [
        c.text for c in app_buffer.completer.get_completions(Document("num"), None)
    ] == ["number"]
    state.state = "UNIT"
    assert [
        c.text for c in app_buffer.completer.get_completions(Document("rp"), None)
    ] == ["rpm"]
    assert [
        c.text for c in app_buffer.completer.get_completions(Document("c"), None)
    ] == ["°C"]

    # 5. enter
    with patch.object(AppState, "dispatch_enter") as mock_dispatch:
        bindings["c-m"](mock_event)
        mock_dispatch.assert_called_once()


def test_app_completion_keybindings(tmp_path: Path) -> None:
    """Test completion-specific keybindings."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    app = create_app(session, table, tmp_path, output=DummyOutput())
    mock_event = MagicMock(spec=KeyPressEvent)

    buffer_ctrl = app.layout.container.content.children[5].children[1]  # type: ignore[attr-defined]
    app_buffer = buffer_ctrl.content.buffer
    assert app.key_bindings is not None
    named_bindings = {b.handler.__name__: b.handler for b in app.key_bindings.bindings}

    with patch.object(app_buffer, "cancel_completion") as mock_cancel:
        named_bindings["_cancel_completion"](mock_event)
        mock_cancel.assert_called_once()

    with patch.object(app_buffer, "complete_previous") as mock_prev:
        named_bindings["_up_completion"](mock_event)
        mock_prev.assert_called_once()

    with patch.object(app_buffer, "complete_next") as mock_next:
        named_bindings["_down_completion"](mock_event)
        mock_next.assert_called_once()

    with patch.object(app_buffer, "start_completion") as mock_start:
        app_buffer.complete_state = None
        named_bindings["_tab"](mock_event)
        mock_start.assert_called_once_with(select_first=False)

    with patch.object(app_buffer, "complete_next") as mock_next:
        app_buffer.complete_state = MagicMock()
        named_bindings["_tab"](mock_event)
        mock_next.assert_called_once()

    with patch.object(app_buffer, "complete_previous") as mock_prev:
        app_buffer.complete_state = MagicMock()
        named_bindings["_s_tab"](mock_event)
        mock_prev.assert_called_once()

    app_buffer.complete_state = None
    named_bindings["_s_tab"](mock_event)


def test_app_scrolling(tmp_path: Path) -> None:
    """Test table scrolling behavior and bounds capping."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    table.update(
        [(i, ParameterValues(value=i, min_value=0, max_value=100)) for i in range(50)]
    )
    app = create_app(session, table, tmp_path, output=DummyOutput())
    state = getattr(app, "state")
    bindings = {b.keys[0]: b.handler for b in app.key_bindings.bindings}  # type: ignore[union-attr]
    mock_event = MagicMock(spec=KeyPressEvent)

    # pagedown & pageup with capping (50 rows, PAGE_SIZE 25 -> max offset 25)
    assert state.scroll_offset == 0
    bindings["pagedown"](mock_event)
    assert state.scroll_offset == 20
    bindings["pagedown"](mock_event)
    assert state.scroll_offset == 25
    bindings["pagedown"](mock_event)
    assert state.scroll_offset == 25
    bindings["pageup"](mock_event)
    assert state.scroll_offset == 5
    bindings["pageup"](mock_event)
    assert state.scroll_offset == 0

    # down & up with capping
    bindings["down"](mock_event)
    assert state.scroll_offset == 1
    bindings["down"](mock_event)
    assert state.scroll_offset == 2
    bindings["up"](mock_event)
    assert state.scroll_offset == 1
    bindings["up"](mock_event)
    assert state.scroll_offset == 0
    bindings["up"](mock_event)
    assert state.scroll_offset == 0

    # empty table cannot scroll
    empty_state = AppState(session, ParameterTable(), tmp_path)
    assert empty_state.max_scroll_offset == 0


async def test_run_app(tmp_path: Path) -> None:
    """Test run_app main loop execution."""
    args = argparse.Namespace(
        url="socket://localhost:8899",
        output=str(tmp_path),
        interval=1.0,
        baudrate=115200,
    )

    product_info = ProductInfo(
        type=ProductType.ECOMAX_P,
        id=90,
        uid="*TEST*",
        logo=0,
        image=0,
        model="ecoMAX 350P2-ZF",
    )

    created_sessions: list[Session] = []
    orig_init = Session.__init__

    def track_init(self: Session, *a: Any, **kw: Any) -> None:
        orig_init(self, *a, **kw)
        created_sessions.append(self)

    with (
        create_pipe_input() as pipe_input,
        create_app_session(input=pipe_input, output=DummyOutput()),
        patch.object(Session, "__init__", track_init),
        patch(
            "pyplumio.cli.session.Session.connect", new_callable=AsyncMock
        ) as mock_connect,
        patch(
            "prompt_toolkit.application.Application.run_async",
            new_callable=AsyncMock,
        ) as mock_run,
        patch(
            "pyplumio.cli.session.Session.close", new_callable=AsyncMock
        ) as mock_close,
    ):

        async def fake_run_async(*_args: Any, **_kwargs: Any) -> None:
            if created_sessions and created_sessions[0]._on_update:
                created_sessions[0]._on_update(
                    [(0, ParameterValues(value=10, min_value=0, max_value=20))],
                    b"\x00" * 40,
                )

        mock_connect.return_value = product_info
        mock_run.side_effect = fake_run_async

        ret = await run_app(args)
        assert ret == 0
        mock_connect.assert_awaited_once()
        mock_run.assert_awaited_once()
        mock_close.assert_awaited_once()


async def test_run_app_error(capsys: pytest.CaptureFixture[str]) -> None:
    """Test run_app handling connection error."""
    args = argparse.Namespace(
        url="socket://localhost:8899",
        output="output",
        interval=1.0,
        baudrate=115200,
    )

    with patch(
        "pyplumio.cli.session.Session.connect",
        side_effect=PyPlumIOError("Connection refused"),
    ):
        ret = await run_app(args)
        assert ret == 1
        captured = capsys.readouterr()
        assert "Error: Connection refused" in captured.err
