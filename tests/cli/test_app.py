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
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.key_binding import KeyPressEvent
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.shortcuts import PromptSession
from prompt_toolkit.validation import ValidationError
import pytest

from pyplumio.cli.app import (
    AppState,
    _get_header_text,
    _get_table_text,
    _save_files,
    create_app,
    prompt_connection_url,
    run_app,
)
from pyplumio.cli.model import ParameterTable
from pyplumio.cli.session import Session
from pyplumio.const import PERCENTAGE, ProductType
from pyplumio.exceptions import PyPlumIOError
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.ecomax import EcomaxNumberDescription
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

    # Step 1: Index
    buff.text = "0"
    state.dispatch_enter(buff)
    assert state.state == "NAME"
    assert state.wizard_data["index"] == 0

    # Step 2: Name
    buff.text = "boiler_temp"
    state.dispatch_enter(buff)
    assert state.state == "TYPE"
    assert state.wizard_data["name"] == "boiler_temp"

    # Step 3: Type number
    buff.text = "number"
    state.dispatch_enter(buff)
    assert state.state == "STEP"

    # Step 4: Step
    buff.text = "1"
    state.dispatch_enter(buff)
    assert state.state == "OFFSET"
    assert state.wizard_data["step"] == 1

    # Step 5: Offset
    buff.text = "0"
    state.dispatch_enter(buff)
    assert state.state == "UNIT"
    assert state.wizard_data["offset"] == 0

    # Step 6: Unit
    buff.text = "%"
    state.dispatch_enter(buff)
    assert state.state == "PREVIEW"

    # Step 7: Preview confirm
    buff.text = "y"
    state.dispatch_enter(buff)
    assert state.state == "INDEX"
    assert 0 in table.descriptions
    desc = table.descriptions[0]
    assert isinstance(desc, EcomaxNumberDescription)
    assert desc.name == "boiler_temp"
    assert desc.unit_of_measurement == PERCENTAGE


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

    buff.text = "0"
    state.dispatch_enter(buff)

    # Name invalid
    buff.text = "123_invalid"
    state.dispatch_enter(buff)
    assert "Name must match" in state.status

    buff.text = "boiler_temp"
    state.dispatch_enter(buff)

    # Type invalid
    buff.text = "unknown"
    state.dispatch_enter(buff)
    assert "Type must be" in state.status

    buff.text = "number"
    state.dispatch_enter(buff)

    # Step invalid
    buff.text = "-5"
    state.dispatch_enter(buff)
    assert "Step must be a positive number" in state.status

    buff.text = "1"
    state.dispatch_enter(buff)

    # Offset invalid
    buff.text = "abc"
    state.dispatch_enter(buff)
    assert "Offset must be an integer" in state.status

    buff.text = "0"
    state.dispatch_enter(buff)

    # Unit invalid
    buff.text = "invalid_unit"
    state.dispatch_enter(buff)
    assert "Unknown unit" in state.status


async def test_app_state_switch_and_decline(tmp_path: Path) -> None:
    """Test AppState wizard with switch and declining preview."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    table.update([(1, ParameterValues(value=1, min_value=0, max_value=1))])
    state = AppState(session, table, tmp_path)
    buff = Buffer()

    # Index -> Name -> Type switch -> Preview -> Decline
    buff.text = "1"
    state.dispatch_enter(buff)
    buff.text = "heating_switch"
    state.dispatch_enter(buff)
    buff.text = "switch"
    state.dispatch_enter(buff)
    assert state.state == "PREVIEW"

    buff.text = "n"
    state.dispatch_enter(buff)
    assert state.state == "INDEX"
    assert state.status == "Discarded."
    assert 1 not in table.descriptions


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
    assert "Saved:" in state.status

    # Test overwrite declined
    state.step_overwrite("n", buff)
    assert state.status == "Save cancelled."

    # Test overwrite accepted
    state.step_overwrite("y", buff)
    assert "Saved:" in state.status

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
    table.update([(0, ParameterValues(value=15, min_value=0, max_value=20))])
    lines = _get_table_text(state)
    assert len(lines) >= 3
    assert "*15" in lines[2][1]


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
    assert "Saved:" in state.status

    # 2c. c-s with product info and existing file
    bindings["c-s"](mock_event)
    assert state.state == "OVERWRITE"
    assert "Overwrite existing" in state.prompt

    # 3. escape
    bindings["escape"](mock_event)
    assert state.state == "INDEX"
    assert state.status == "Cancelled."

    # 4. pagedown & pageup
    assert state.scroll_offset == 0
    bindings["pagedown"](mock_event)
    assert state.scroll_offset == 20
    bindings["pageup"](mock_event)
    assert state.scroll_offset == 0

    # 5. enter
    with patch.object(AppState, "dispatch_enter") as mock_dispatch:
        bindings["c-m"](mock_event)
        mock_dispatch.assert_called_once()


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
