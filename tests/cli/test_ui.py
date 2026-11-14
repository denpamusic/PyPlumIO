"""Contains tests for the CLI UI module."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
import zipfile

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import OneStyleAndTextTuple
from prompt_toolkit.key_binding import KeyPressEvent
from prompt_toolkit.output import DummyOutput

from pyplumio.cli.model import ParameterTable
from pyplumio.cli.session import Session
from pyplumio.cli.state import AppState, AppStep
from pyplumio.cli.ui import (
    PREVIEW_BOX_WIDTH,
    TABLE_HEADER,
    TABLE_SEPARATOR,
    _get_completer,
    _get_header_text,
    _get_preview_text,
    _get_table_text,
    create_app,
)
from pyplumio.const import PERCENTAGE, ProductType, UnitOfMeasurement
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.ecomax import EcomaxNumberDescription, EcomaxSwitchDescription
from pyplumio.structures.product_info import ProductInfo


def _step(state: AppState) -> AppStep:
    """Return app step without triggering mypy attribute narrowing."""
    return state.step


def _assert_table_row(line: OneStyleAndTextTuple, index: int, style: str) -> None:
    """Assert formatted table row index and style."""
    assert f"    {index}  " in line[1]
    assert line[0] == style


async def test_app_state_save_nothing_mapped(tmp_path: Path) -> None:
    """Test saving files when no descriptions are mapped."""
    session = Session(url="socket://localhost:8899")
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
    table = ParameterTable()
    app, state = create_app(session, table, tmp_path, output=DummyOutput())
    assert app.key_bindings is not None
    bindings = {b.keys[0]: b.handler for b in app.key_bindings.bindings}
    mock_event = MagicMock(spec=KeyPressEvent)

    bindings["c-s"](mock_event)
    assert state.status == "Nothing to save: map at least one parameter first."


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

    # Table text without description
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

    # Table text with units and column alignment verification
    table.set_description(
        0,
        EcomaxNumberDescription(
            name="boiler_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
    )
    table.update(
        [
            (0, ParameterValues(value=75, min_value=10, max_value=85)),
            (1, ParameterValues(value=1, min_value=0, max_value=1)),
            (2, ParameterValues(value=50, min_value=0, max_value=100)),
        ]
    )
    table.set_description(1, EcomaxSwitchDescription(name="heating_pump"))
    table.set_description(
        2,
        EcomaxNumberDescription(name="fan_power", unit_of_measurement=PERCENTAGE),
    )
    lines = _get_table_text(state)

    # Check header and separator lines
    assert lines[0] == ("bold", TABLE_HEADER)
    assert lines[1] == ("bold", TABLE_SEPARATOR)
    assert TABLE_HEADER == (
        "Index  Name                                  Value       Min         Max\n"
    )
    assert (
        f"{'-' * 5}  {'-' * 36}  {'-' * 10}  {'-' * 10}  {'-' * 10}\n"
    ) == TABLE_SEPARATOR

    # Verify column alignment across rows
    rows_by_index = {int(line[1].split()[0]): line[1] for line in lines[2:]}
    assert (
        rows_by_index[0]
        == f"{0:>5}  {'boiler_temp':<36}  {'75 °C':<10}  {'10 °C':<10}  {'85 °C':<10}\n"
    )
    assert (
        rows_by_index[1]
        == f"{1:>5}  {'heating_pump':<36}  {'on':<10}  {'off':<10}  {'on':<10}\n"
    )
    assert (
        rows_by_index[2]
        == f"{2:>5}  {'fan_power':<36}  {'50 %':<10}  {'0 %':<10}  {'100 %':<10}\n"
    )


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

    # 1. INDEX state - empty buffer
    buff.text = ""
    lines = _get_preview_text(state, buff)
    assert len(lines) == 1
    content = lines[0][1]
    assert "┌─ Live Preview" in content
    assert "Enter a parameter index below to preview raw values" in content
    assert len(content.splitlines()) == 4
    assert all(len(line) == PREVIEW_BOX_WIDTH for line in content.splitlines())

    # 1b. INDEX state - non-digit or non-existent index
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
    assert _step(state) == AppStep.NAME
    buff.text = ""
    content = _get_preview_text(state, buff)[0][1]
    assert "[Name: <unnamed>]" in content

    buff.text = "boiler_power"
    content = _get_preview_text(state, buff)[0][1]
    assert "[Name: boiler_power]" in content
    assert "Type: number" in content

    # 2b. NAME state with switch row
    state.reset_app(buff)
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

    # Enter editing and advance to TYPE
    buff.text = "0"
    state.dispatch_enter(buff)
    buff.text = "boiler_power"
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.TYPE

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
    assert _step(state) == AppStep.OFFSET

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
    assert _step(state) == AppStep.STEP
    assert state.data.offset == 5

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
    state.data.index = 0
    state.data.name = "boiler_power"
    state.data.offset = 5
    state.data.step = 0.5
    state.step = AppStep.UNIT
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
    assert "Preview: 7.5 % (2.5-12.5 %)" in content
    buff.text = "invalid_unit"
    assert "[Unit: none]" in _get_preview_text(state, buff)[0][1]

    # Advance to COMMENT and CONFIRM states
    buff.text = "°C"
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.COMMENT
    content = _get_preview_text(state, buff)[0][1]
    assert "Name: boiler_power" in content
    assert "Unit: °C" in content
    assert "Preview: 7.5 °C (2.5-12.5 °C)" in content

    buff.text = ""
    state.dispatch_enter(buff)
    assert _step(state) == AppStep.CONFIRM
    content = _get_preview_text(state, buff)[0][1]
    assert "Name: boiler_power" in content
    assert "Type: number" in content
    assert "Offset: 5" in content
    assert "Step: 0.5" in content
    assert "Unit: °C" in content
    assert "Preview: 7.5 °C (2.5-12.5 °C)" in content

    # OVERWRITE state
    state.step = AppStep.OVERWRITE
    assert "Live Preview (Index #0)" in _get_preview_text(state, buff)[0][1]

    # Clamping long names
    state.data.name = "a" * 80
    long_content = _get_preview_text(state, buff)[0][1]
    assert len(long_content.splitlines()) == 4
    assert all(len(line) == PREVIEW_BOX_WIDTH for line in long_content.splitlines())


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

    # Clear changed on parameter 1 via app selection
    buff = Buffer()
    buff.text = "1"
    state.dispatch_enter(buff)
    lines = _get_table_text(state)
    _assert_table_row(lines[2], 1, "")
    _assert_table_row(lines[3], 2, "reverse")
    _assert_table_row(lines[4], 0, "")

    state.reset_app(buff)

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
    app, state = create_app(session, table, tmp_path, output=DummyOutput())

    assert app.key_bindings is not None
    bindings = {b.keys[0]: b.handler for b in app.key_bindings.bindings}
    mock_event = MagicMock(spec=KeyPressEvent)
    mock_event.app = MagicMock()
    buffer_ctrl = app.layout.container.content.children[5].children[1]  # type: ignore[attr-defined]
    app_buffer = buffer_ctrl.content.buffer

    # 1. c-q
    bindings["c-q"](mock_event)
    mock_event.app.exit.assert_called_once()

    # 2. c-s without product info
    bindings["c-s"](mock_event)
    assert state.status == "No connection or product info yet."

    # 2b. c-s with product info but nothing mapped
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
    assert state.status == "Nothing to save: map at least one parameter first."

    # 2c. c-s with product info and mapped description -> ZIP question -> file tree
    table.set_description(0, EcomaxNumberDescription(name="boiler_temp"))
    bindings["c-s"](mock_event)
    assert _step(state) == AppStep.ZIP
    assert state.prompt == "Save as a ZIP archive? [y/N]: "
    state.step_zip("n", app_buffer)
    assert _step(state) == AppStep.INDEX
    assert state.status == f"Files saved to {tmp_path}."

    # 2d. c-s with product info and existing file -> ZIP question -> OVERWRITE
    bindings["c-s"](mock_event)
    assert _step(state) == AppStep.ZIP
    state.step_zip("n", app_buffer)
    assert _step(state) == AppStep.OVERWRITE
    assert state.prompt == "Overwrite existing ecomax_350p2_zf.py? [y/N]: "
    assert str(tmp_path) not in state.prompt

    # 3. escape
    bindings["escape"](mock_event)
    assert _step(state) == AppStep.INDEX
    assert state.status == "Cancelled."

    # 4. live preview container check
    preview_win = app.layout.container.content.children[3]  # type: ignore[attr-defined]
    assert preview_win.height == 4
    preview_output = preview_win.content.text()
    assert "Live Preview" in preview_output[0][1]

    # 5. completer checks
    assert app_buffer.completer is not None
    assert (
        list(app_buffer.completer.get_completions(Document(""), CompleteEvent())) == []
    )
    state.step = AppStep.TYPE
    assert [
        c.text
        for c in app_buffer.completer.get_completions(Document("num"), CompleteEvent())
    ] == ["number"]
    state.step = AppStep.UNIT
    assert [
        c.text
        for c in app_buffer.completer.get_completions(Document("rp"), CompleteEvent())
    ] == ["rpm"]
    assert [
        c.text
        for c in app_buffer.completer.get_completions(Document("c"), CompleteEvent())
    ] == ["°C"]

    # 6. enter
    with patch.object(AppState, "dispatch_enter") as mock_dispatch:
        bindings["c-m"](mock_event)
        mock_dispatch.assert_called_once()


def test_app_completion_keybindings(tmp_path: Path) -> None:
    """Test completion-specific keybindings."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    app, _state = create_app(session, table, tmp_path, output=DummyOutput())
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
    app, state = create_app(session, table, tmp_path, output=DummyOutput())
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


def test_create_app_returns_tuple() -> None:
    """Test create_app returns a tuple of Application and AppState."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    app, state = create_app(session, table, Path.cwd(), output=DummyOutput())
    assert isinstance(app, Application)
    assert isinstance(state, AppState)
    assert state.application is app
    assert state.session is session
    assert state.table is table


def test_name_completer(tmp_path: Path) -> None:
    """Test NAME-step autocompletion for standard ecoMAX parameter names."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    table.update(
        [
            (0, ParameterValues(value=20, min_value=10, max_value=30)),
            (1, ParameterValues(value=15, min_value=10, max_value=30)),
        ]
    )
    app, state = create_app(session, table, tmp_path, output=DummyOutput())
    buffer_ctrl = app.layout.container.content.children[5].children[1]  # type: ignore[attr-defined]
    app_buffer = buffer_ctrl.content.buffer
    assert app_buffer.completer is not None

    # No completions at NAME step when product_info is None
    state.step = AppStep.NAME
    state.data.index = 0
    assert _get_completer(state) is None
    assert (
        list(app_buffer.completer.get_completions(Document("curve"), CompleteEvent()))
        == []
    )

    # With product_info, offers substring matches for ProductType
    session.product_info = ProductInfo(
        type=ProductType.ECOMAX_P,
        id=90,
        uid="*TEST*",
        logo=0,
        image=0,
        model="ecoMAX 350P2-ZF",
    )
    matches = [
        c.text
        for c in app_buffer.completer.get_completions(
            Document("curve"), CompleteEvent()
        )
    ]
    assert matches == ["heating_curve", "heating_curve_shift"]

    # Excludes names used by other indices, keeps name used by current index
    table.set_description(0, EcomaxNumberDescription(name="heating_curve_shift"))
    table.set_description(1, EcomaxNumberDescription(name="heating_curve"))
    matches = [
        c.text
        for c in app_buffer.completer.get_completions(
            Document("curve"), CompleteEvent()
        )
    ]
    assert matches == ["heating_curve_shift"]

    state.step = AppStep.TYPE
    assert [
        c.text
        for c in app_buffer.completer.get_completions(Document("sw"), CompleteEvent())
    ] == ["switch"]
    state.step = AppStep.UNIT
    assert [
        c.text
        for c in app_buffer.completer.get_completions(Document("kg"), CompleteEvent())
    ] == ["kg", "kWh/kg", "kg/h"]
    state.step = AppStep.ZIP
    assert _get_completer(state) is None


def test_live_preview_box_prefilled_unit_and_step(tmp_path: Path) -> None:
    """Test live preview box with pre-filled step and unit defaults."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    table.update([(0, ParameterValues(value=25, min_value=10, max_value=40))])
    state = AppState(session, table, tmp_path)
    state.data.index = 0
    state.data.name = "curve_shift"
    state.data.offset = 20
    state.data.step = 0.2
    state.data.unit = UnitOfMeasurement.CELSIUS
    buff = Buffer()

    # STEP state with pre-filled step
    state.step = AppStep.STEP
    buff.text = ""
    assert "[Step: 0.2]" in _get_preview_text(state, buff)[0][1]
    buff.text = "-1"
    assert "[Step: 0.2]" in _get_preview_text(state, buff)[0][1]
    buff.text = "0.5"
    assert "[Step: 0.5]" in _get_preview_text(state, buff)[0][1]

    # UNIT state with pre-filled unit
    state.step = AppStep.UNIT
    buff.text = ""
    content = _get_preview_text(state, buff)[0][1]
    assert "[Unit: °C]" in content
    assert "Preview: 1.0 °C (-2.0-4.0 °C)" in content

    buff.text = "kW"
    content = _get_preview_text(state, buff)[0][1]
    assert "[Unit: kW]" in content
    assert "Preview: 1.0 kW (-2.0-4.0 kW)" in content

    buff.text = "none"
    content = _get_preview_text(state, buff)[0][1]
    assert "[Unit: none]" in content
    assert "Preview: 1.0 (-2.0-4.0)" in content

    buff.text = "invalid_unit"
    content = _get_preview_text(state, buff)[0][1]
    assert "[Unit: °C]" in content


async def test_zip_save_flow_tree_and_cancel(tmp_path: Path) -> None:
    """Test ZIP prompt, tree save, overwrite prompt, Esc cancel, and live preview."""
    session = Session(url="socket://localhost:8899")
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
    table = ParameterTable()
    table.update([(0, ParameterValues(value=10, min_value=0, max_value=20))])
    table.set_description(0, EcomaxNumberDescription(name="boiler_temp"))

    app, state = create_app(session, table, tmp_path, output=DummyOutput())
    assert app.key_bindings is not None
    bindings = {b.keys[0]: b.handler for b in app.key_bindings.bindings}
    mock_event = MagicMock(spec=KeyPressEvent)
    buffer_ctrl = app.layout.container.content.children[5].children[1]  # type: ignore[attr-defined]
    app_buffer = buffer_ctrl.content.buffer

    # Ctrl+S asks ZIP question; Esc cancels back to INDEX
    bindings["c-s"](mock_event)
    assert _step(state) == AppStep.ZIP
    assert state.prompt == "Save as a ZIP archive? [y/N]: "
    bindings["escape"](mock_event)
    assert _step(state) == AppStep.INDEX
    assert state.status == "Cancelled."
    assert state.data.save_as_zip is False

    # Live preview at AppStep.ZIP while editing an index; empty answer writes tree
    app_buffer.text = "0"
    state.dispatch_enter(app_buffer)
    bindings["c-s"](mock_event)
    assert _step(state) == AppStep.ZIP
    assert "Live Preview (Index #0)" in _get_preview_text(state, app_buffer)[0][1]
    app_buffer.text = ""
    state.dispatch_enter(app_buffer)
    assert _step(state) == AppStep.INDEX
    assert state.status == f"Files saved to {tmp_path}."
    assert state.data.save_as_zip is False
    assert (tmp_path / "pyplumio/parameters/custom/ecomax_350p2_zf.py").is_file()

    # Answering "n" with existing .py goes to OVERWRITE; Esc cancels
    bindings["c-s"](mock_event)
    state.step_zip("n", app_buffer)
    assert _step(state) == AppStep.OVERWRITE
    assert state.prompt == "Overwrite existing ecomax_350p2_zf.py? [y/N]: "
    bindings["escape"](mock_event)
    assert _step(state) == AppStep.INDEX
    assert state.status == "Cancelled."


async def test_zip_save_flow_archive(tmp_path: Path) -> None:
    """Test answering yes at ZIP prompt creates and overwrites ZIP archive."""
    session = Session(url="socket://localhost:8899")
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
    table = ParameterTable()
    table.update([(0, ParameterValues(value=10, min_value=0, max_value=20))])
    table.set_description(0, EcomaxNumberDescription(name="boiler_temp"))

    app, state = create_app(session, table, tmp_path, output=DummyOutput())
    assert app.key_bindings is not None
    bindings = {b.keys[0]: b.handler for b in app.key_bindings.bindings}
    mock_event = MagicMock(spec=KeyPressEvent)
    buffer_ctrl = app.layout.container.content.children[5].children[1]  # type: ignore[attr-defined]
    app_buffer = buffer_ctrl.content.buffer
    zip_path = tmp_path / "ecomax_350p2_zf.zip"

    # Answering "y" writes ZIP and resets save_as_zip
    bindings["c-s"](mock_event)
    state.step_zip("y", app_buffer)
    assert _step(state) == AppStep.INDEX
    assert state.status == f"Files saved to {zip_path}."
    assert state.data.save_as_zip is False
    assert zip_path.is_file()
    with zipfile.ZipFile(zip_path, "r") as archive:
        assert set(archive.namelist()) == {
            "pyplumio/parameters/custom/ecomax_350p2_zf.py",
            "tests/parameters/custom/test_ecomax_350p2_zf.py",
            "tests/testdata/parameters/ecomax_350p2_zf.json",
        }

    # Existing ZIP -> OVERWRITE prompt, decline -> "Save cancelled."
    bindings["c-s"](mock_event)
    state.step_zip("y", app_buffer)
    assert _step(state) == AppStep.OVERWRITE
    assert state.prompt == "Overwrite existing ecomax_350p2_zf.zip? [y/N]: "
    assert bool(state.data.save_as_zip) is True
    state.step_overwrite("n", app_buffer)
    assert _step(state) == AppStep.INDEX
    assert state.status == "Save cancelled."
    assert state.data.save_as_zip is False

    # Existing ZIP -> OVERWRITE accept -> rewrites ZIP and resets save_as_zip
    bindings["c-s"](mock_event)
    state.step_zip("yes", app_buffer)
    assert _step(state) == AppStep.OVERWRITE
    state.step_overwrite("y", app_buffer)
    assert _step(state) == AppStep.INDEX
    assert state.status == f"Files saved to {zip_path}."
    assert state.data.save_as_zip is False


async def test_zip_save_flag(tmp_path: Path) -> None:
    """Test create_app with zip_output=True skips ZIP prompt and saves ZIP directly."""
    session = Session(url="socket://localhost:8899")
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
    table = ParameterTable()
    table.update([(0, ParameterValues(value=10, min_value=0, max_value=20))])
    table.set_description(0, EcomaxNumberDescription(name="boiler_temp"))

    app, state = create_app(
        session, table, tmp_path, output=DummyOutput(), zip_output=True
    )
    assert app.key_bindings is not None
    bindings = {b.keys[0]: b.handler for b in app.key_bindings.bindings}
    mock_event = MagicMock(spec=KeyPressEvent)
    buffer_ctrl = app.layout.container.content.children[5].children[1]  # type: ignore[attr-defined]
    app_buffer = buffer_ctrl.content.buffer

    zip_path = tmp_path / "ecomax_350p2_zf.zip"
    bindings["c-s"](mock_event)
    assert _step(state) == AppStep.INDEX
    assert state.status == f"Files saved to {zip_path}."
    assert state.data.save_as_zip is False
    assert zip_path.is_file()

    # Second Ctrl+S goes directly to OVERWRITE for the ZIP file
    bindings["c-s"](mock_event)
    assert _step(state) == AppStep.OVERWRITE
    assert state.prompt == "Overwrite existing ecomax_350p2_zf.zip? [y/N]: "
    app_buffer.text = "y"
    state.dispatch_enter(app_buffer)
    assert _step(state) == AppStep.INDEX
    assert state.status == f"Files saved to {zip_path}."
    assert state.data.save_as_zip is False
