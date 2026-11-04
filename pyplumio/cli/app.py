"""Contains prompt_toolkit full-screen Application for PyPlumIO CLI."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from contextlib import suppress
from pathlib import Path
import re
import sys
from typing import Any, Final, Literal

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import DynamicCompleter, WordCompleter
from prompt_toolkit.filters import has_completions
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.input import Input
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.layout.containers import (
    Float,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.output import Output
from prompt_toolkit.shortcuts import PromptSession
from prompt_toolkit.validation import Validator

from pyplumio.cli.codegen import generate_all_files, write_files
from pyplumio.cli.model import ParameterTable, Row, load_custom_parameters
from pyplumio.cli.session import Session
from pyplumio.const import PERCENTAGE, UnitOfMeasurement
from pyplumio.exceptions import PyPlumIOError
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.custom import model_slug
from pyplumio.parameters.ecomax import EcomaxNumberDescription, EcomaxSwitchDescription

DEFAULT_PORT: Final = 8899
MAX_PORT: Final = 65535
NAME_REGEX: Final = re.compile(r"^[a-z][a-z0-9_]*$")
PAGE_SIZE: Final = 25
SCROLL_PAGE: Final = 20
INDEX_PROMPT: Final = "Enter parameter index to edit: "
UNIT_WORDS: Final = tuple(u.value for u in UnitOfMeasurement) + (PERCENTAGE,)
UNIT_ALIASES: Final[dict[str, UnitOfMeasurement | Literal["%"]]] = {
    "%": PERCENTAGE,
    "percent": PERCENTAGE,
    "percentage": PERCENTAGE,
    "c": UnitOfMeasurement.CELSIUS,
    "degc": UnitOfMeasurement.CELSIUS,
    "d": UnitOfMeasurement.DAYS,
    "day": UnitOfMeasurement.DAYS,
    "days": UnitOfMeasurement.DAYS,
    "sec": UnitOfMeasurement.SECONDS,
    "second": UnitOfMeasurement.SECONDS,
    "seconds": UnitOfMeasurement.SECONDS,
    "min": UnitOfMeasurement.MINUTES,
    "minute": UnitOfMeasurement.MINUTES,
    "minutes": UnitOfMeasurement.MINUTES,
}
UNIT_COMPLETER: Final = WordCompleter(
    list(UNIT_WORDS),
    ignore_case=True,
    match_middle=True,
    meta_dict={
        **{u.value: u.name.replace("_", " ").lower() for u in UnitOfMeasurement},
        PERCENTAGE: "percentage",
    },
)
TYPE_COMPLETER: Final = WordCompleter(["number", "switch"])
TABLE_HEADER: Final = (
    "Index  Name                                  Value       Min         Max\n"
)
TABLE_SEPARATOR: Final = f"{'-' * 5}  {'-' * 36}  {'-' * 10}  {'-' * 10}  {'-' * 10}\n"
PREVIEW_BOX_WIDTH: Final = 78


async def prompt_connection_url(
    prompt_session: PromptSession[str] | None = None,
) -> str:
    """Prompt user for connection details and return the connection URL."""
    session = prompt_session or PromptSession()
    type_val = Validator.from_callable(
        lambda t: t.strip().lower() in ("tcp", "serial"),
        error_message="Must be 'tcp' or 'serial'",
    )
    conn = (
        (
            await session.prompt_async(
                "Connection type (tcp/serial): ",
                completer=WordCompleter(["tcp", "serial"]),
                validator=type_val,
            )
        )
        .strip()
        .lower()
    )
    if conn == "tcp":
        host_val = Validator.from_callable(
            lambda t: bool(t.strip()), error_message="Host cannot be empty"
        )
        host = (await session.prompt_async("Host: ", validator=host_val)).strip()
        port_val = Validator.from_callable(
            lambda t: (
                not t.strip() or (t.strip().isdigit() and 1 <= int(t) <= MAX_PORT)
            ),
            error_message=f"Port must be 1-{MAX_PORT}",
        )
        port = (
            await session.prompt_async(f"Port [{DEFAULT_PORT}]: ", validator=port_val)
        ).strip()
        return f"socket://{host}:{int(port) if port else DEFAULT_PORT}"
    url_val = Validator.from_callable(
        lambda t: bool(t.strip()), error_message="URL cannot be empty"
    )
    return (
        await session.prompt_async(
            "Device URL (e.g. /dev/ttyUSB0, COM3): ", validator=url_val
        )
    ).strip()


class AppState:
    """Represents application UI and wizard state."""

    __slots__ = (
        "application",
        "output_dir",
        "prompt",
        "scroll_offset",
        "session",
        "state",
        "status",
        "table",
        "wizard_data",
    )

    application: Application[None] | None
    output_dir: Path
    prompt: str
    scroll_offset: int
    session: Session
    state: str
    status: str
    table: ParameterTable
    wizard_data: dict[str, Any]

    def __init__(
        self, session: Session, table: ParameterTable, output_dir: Path
    ) -> None:
        """Initialize application state."""
        self.session, self.table, self.output_dir = session, table, output_dir
        self.state, self.prompt, self.status = "INDEX", INDEX_PROMPT, ""
        self.scroll_offset, self.wizard_data, self.application = 0, {}, None

    @property
    def max_scroll_offset(self) -> int:
        """Return maximum scroll offset."""
        return max(0, len(self.table) - PAGE_SIZE)

    def _set_state(
        self, state: str, prompt: str, buffer: Buffer, text: str = "", status: str = ""
    ) -> None:
        """Update wizard state and prompt buffer."""
        self.state, self.prompt, buffer.text, self.status = state, prompt, text, status

    def reset_wizard(self, buffer: Buffer) -> None:
        """Reset wizard back to index prompt."""
        self.state, self.prompt, buffer.text = "INDEX", INDEX_PROMPT, ""
        self.wizard_data.clear()

    def step_index(self, text: str, buffer: Buffer) -> None:
        """Handle index step."""
        if text.isdigit() and (row := self.table.get(index := int(text))):
            self.table.clear_changed(index)
            self.wizard_data["index"] = index
            self._set_state("NAME", "Name: ", buffer, text=row.name)
            buffer.cursor_position = len(row.name)
        else:
            self._set_state(
                "INDEX", INDEX_PROMPT, buffer, status="Index must exist in table."
            )

    def step_name(self, text: str, buffer: Buffer) -> None:
        """Handle name step."""
        if not NAME_REGEX.match(text):
            self.status = (
                "Name must start with a lowercase letter and contain only "
                "lowercase letters, numbers, and underscores."
            )
            return
        self.wizard_data["name"] = text
        row = self.table.get(self.wizard_data["index"])
        is_switch = (
            row is not None and row.values.min_value == 0 and row.values.max_value == 1
        )
        default_type = "switch" if is_switch else "number"
        self.wizard_data["default_type"] = default_type
        self._set_state(
            "TYPE", f"Parameter type (number, switch) [{default_type}]: ", buffer
        )

    def step_type(self, text: str, buffer: Buffer) -> None:
        """Handle type step."""
        row = self.table.get(self.wizard_data.get("index", -1))
        is_switch = (
            row is not None and row.values.min_value == 0 and row.values.max_value == 1
        )
        default_type = self.wizard_data.get(
            "default_type", "switch" if is_switch else "number"
        )
        choice = text.lower() or default_type
        if choice == "switch":
            self.setup_confirm(
                EcomaxSwitchDescription(name=self.wizard_data["name"]), buffer
            )
        elif choice == "number":
            self._set_state("OFFSET", "Offset [0]: ", buffer)
        else:
            self.status = "Type must be 'number' or 'switch'."

    def step_offset(self, text: str, buffer: Buffer) -> None:
        """Handle offset step."""
        try:
            self.wizard_data["offset"] = int(text) if text else 0
            self._set_state("STEP", "Step [1]: ", buffer)
        except ValueError:
            self.status = "Offset must be an integer."

    def step_step(self, text: str, buffer: Buffer) -> None:
        """Handle step step."""
        try:
            if (step := float(text) if text else 1.0) <= 0:
                raise ValueError
            self.wizard_data["step"] = int(step) if step.is_integer() else step
            units_display = ", ".join(UNIT_WORDS)
            self._set_state(
                "UNIT",
                "Unit [none]: ",
                buffer,
                status=f"Available units: {units_display}",
            )
        except ValueError:
            self.status = "Step must be a positive number."

    def step_unit(self, text: str, buffer: Buffer) -> None:
        """Handle unit step."""
        unit = _parse_unit(text)
        if unit is False:
            units_display = ", ".join(UNIT_WORDS)
            self.status = f"Unknown unit of measurement. Available: {units_display}"
            return
        self.setup_confirm(
            EcomaxNumberDescription(
                name=self.wizard_data["name"],
                step=self.wizard_data["step"],
                offset=self.wizard_data["offset"],
                unit_of_measurement=unit,
            ),
            buffer,
        )

    def setup_confirm(
        self,
        description: EcomaxNumberDescription | EcomaxSwitchDescription,
        buffer: Buffer,
    ) -> None:
        """Set up confirm prompt."""
        row = self.table.get(self.wizard_data["index"])
        preview = Row(0, row.values, description=description) if row else None
        val, min_val, max_val = (
            (preview.value, preview.min_value, preview.max_value)
            if preview
            else ("", "", "")
        )
        unit = getattr(description, "unit_of_measurement", None)
        u_str = f"{unit}" if unit == PERCENTAGE else f" {unit}" if unit else ""
        self.wizard_data["description"] = description
        name = self.wizard_data["name"]
        prompt = (
            f"{name}: {val}{u_str} ({min_val}-{max_val}{u_str}). "
            "Does this match your device? [y/N]: "
        )
        self._set_state("CONFIRM", prompt, buffer)

    def step_confirm(self, text: str, buffer: Buffer) -> None:
        """Handle confirm step."""
        if text.lower() in ("y", "yes"):
            self.table.set_description(
                self.wizard_data["index"], self.wizard_data["description"]
            )
            self.status = f"Stored parameter {self.wizard_data['index']}."
        else:
            self.status = "Discarded."
        self.reset_wizard(buffer)

    def step_overwrite(self, text: str, buffer: Buffer) -> None:
        """Handle overwrite step."""
        if text.lower() in ("y", "yes"):
            _save_files(self)
        else:
            self.status = "Save cancelled."
        self.reset_wizard(buffer)

    def dispatch_enter(self, buffer: Buffer) -> None:
        """Dispatch enter key press to current step handler."""
        if handler := getattr(self, f"step_{self.state.lower()}", None):
            handler(buffer.text.strip(), buffer)


def _parse_unit(
    text: str,
) -> UnitOfMeasurement | Literal["%"] | None | Literal[False]:
    """Parse unit of measurement from user input."""
    if not (text := text.strip()) or text.lower() == "none":
        return None
    if text.lower() in UNIT_ALIASES:
        return UNIT_ALIASES[text.lower()]
    with suppress(ValueError):
        return UnitOfMeasurement(text)
    for unit in UnitOfMeasurement:
        if unit.value.lower() == text.lower():
            return unit
    with suppress(KeyError):
        return UnitOfMeasurement[text.upper()]
    return False


def _save_files(state: AppState) -> None:
    """Save parameter files to disk."""
    info, msg, params = (
        state.session.product_info,
        state.session.last_frame_message,
        state.session.last_parameters,
    )
    if not info or not msg or not params:
        state.status = "Error: no data received yet."
        return
    try:
        files = generate_all_files(
            info,
            state.table.descriptions,
            state.table.overrides,
            msg,
            params,
            state.output_dir,
        )
        write_files(files)
        state.status = f"Files saved to {state.output_dir}."
    except Exception as err:
        state.status = f"Error saving files: {err}"


def _get_header_text(state: AppState) -> StyleAndTextTuples:
    """Return formatted header text."""
    product, last_update = state.session.product_info, state.session.last_update_time
    model, product_id = (product.model, product.id) if product else ("Unknown", 0)
    updated = last_update.strftime("%H:%M:%S") if last_update else "Never"
    return [
        (
            "bold",
            f"Model: {model} (ID: {product_id}) | URL: {state.session.url} | "
            f"Updated: {updated} | Ctrl+S save · Ctrl+Q quit\n",
        )
    ]


def _format_value_with_unit(
    value: Any,
    description: EcomaxNumberDescription | EcomaxSwitchDescription | None,
) -> str:
    """Format parameter value with unit of measurement if available."""
    if isinstance(description, EcomaxSwitchDescription) or not (
        unit := getattr(description, "unit_of_measurement", None)
    ):
        return str(value)
    if unit == PERCENTAGE:
        return f"{value}%"
    return f"{value} {unit}"


def _get_table_text(state: AppState) -> StyleAndTextTuples:
    """Return formatted table text."""
    lines: StyleAndTextTuples = [("bold", TABLE_HEADER), ("bold", TABLE_SEPARATOR)]
    offset = min(state.scroll_offset, state.max_scroll_offset)
    for row in state.table.rows()[offset : offset + PAGE_SIZE]:
        val = _format_value_with_unit(row.value, row.description)
        min_val = _format_value_with_unit(row.min_value, row.description)
        max_val = _format_value_with_unit(row.max_value, row.description)
        row_text = (
            f"{row.index:>5}  {row.name:<36}  {val:<10}  {min_val:<10}  {max_val:<10}\n"
        )
        lines.append(("reverse", row_text) if row.changed else ("", row_text))
    return lines


def _format_field(label: str, value: Any, active: bool) -> str:
    """Format a single preview field, bracketing it when active."""
    text = f"{label}: {value}"
    return f"[{text}]" if active else text


def _resolve_preview_row(state: AppState, text: str) -> Row | None:
    """Return the Row currently being previewed."""
    if "index" in state.wizard_data:
        return state.table.get(state.wizard_data["index"])
    if state.state == "INDEX" and text.isdigit():
        return state.table.get(int(text))
    return None


def _resolve_live_number_params(
    state: AppState, text: str
) -> tuple[int, float | int, UnitOfMeasurement | Literal["%"] | None]:
    """Return live (offset, step, unit) from wizard data and current buffer."""
    offset: int = state.wizard_data.get("offset", 0)
    if state.state == "OFFSET" and text:
        with suppress(ValueError):
            offset = int(text)

    step: float | int = state.wizard_data.get("step", 1)
    if state.state == "STEP" and text:
        with suppress(ValueError):
            if (parsed := float(text)) > 0:
                step = int(parsed) if parsed.is_integer() else parsed

    unit: UnitOfMeasurement | Literal["%"] | None = None
    if state.state == "UNIT":
        parsed_unit = _parse_unit(text)
        unit = None if parsed_unit is False else parsed_unit
    return offset, step, unit


def _build_live_description(
    state: AppState, row: Row, text: str
) -> EcomaxNumberDescription | EcomaxSwitchDescription | None:
    """Build transient description for live preview."""
    if state.state == "INDEX":
        return row.description
    if state.state in ("CONFIRM", "OVERWRITE"):
        return state.wizard_data.get("description", row.description)
    name = text if state.state == "NAME" else state.wizard_data.get("name", row.name)
    name = name or "<unnamed>"
    if (
        state.state == "NAME"
        and isinstance(row.description, EcomaxSwitchDescription)
        or state.state == "TYPE"
        and (text.lower() or state.wizard_data.get("default_type")) == "switch"
    ):
        return EcomaxSwitchDescription(name=name)
    if state.state in ("NAME", "TYPE"):
        return EcomaxNumberDescription(name=name)
    offset, step, unit = _resolve_live_number_params(state, text)
    return EcomaxNumberDescription(
        name=name, step=step, offset=offset, unit_of_measurement=unit
    )


def _get_preview_text(state: AppState, buffer: Buffer) -> StyleAndTextTuples:
    """Return formatted 4-line live preview box."""
    text = buffer.text.strip()
    row = _resolve_preview_row(state, text)
    inner_width = PREVIEW_BOX_WIDTH - 4
    if row is None:
        top = f"┌─ Live Preview {'─' * (PREVIEW_BOX_WIDTH - 17)}┐\n"
        msg = (
            "Enter a parameter index below to preview raw values and live calculations."
        )
        mid1 = f"│ {msg:<{inner_width}} │\n"
        mid2 = f"│ {'':<{inner_width}} │\n"
        bot = f"└{'─' * (PREVIEW_BOX_WIDTH - 2)}┘\n"
        return [("", top + mid1 + mid2 + bot)]

    desc = _build_live_description(state, row, text)
    preview = Row(row.index, row.values, description=desc)
    is_switch = isinstance(desc, EcomaxSwitchDescription)
    type_str = "switch" if is_switch else "number"
    offset_val = getattr(desc, "offset", 0)
    step_val = getattr(desc, "step", 1)
    unit_val = getattr(desc, "unit_of_measurement", None)
    u_str = (
        f"{unit_val}" if unit_val == PERCENTAGE else f" {unit_val}" if unit_val else ""
    )

    fields = [
        _format_field("Name", preview.name or "<unnamed>", state.state == "NAME"),
        _format_field("Type", type_str, state.state == "TYPE"),
    ]
    if not is_switch:
        fields.extend(
            [
                _format_field("Offset", offset_val, state.state == "OFFSET"),
                _format_field("Step", step_val, state.state == "STEP"),
                _format_field("Unit", unit_val or "none", state.state == "UNIT"),
            ]
        )
    line1_content = "  ".join(fields)[:inner_width]
    raw = row.values
    preview_range = f"{preview.min_value}-{preview.max_value}{u_str}"
    line2_content = (
        f"Raw: {raw.value} (min: {raw.min_value}, max: {raw.max_value})  ──►  "
        f"Preview: {preview.value}{u_str} ({preview_range})"
    )[:inner_width]
    header_title = f"─ Live Preview (Index #{row.index}) "
    top = f"┌{header_title}{'─' * max(0, PREVIEW_BOX_WIDTH - 2 - len(header_title))}┐\n"
    mid1 = f"│ {line1_content:<{inner_width}} │\n"
    mid2 = f"│ {line2_content:<{inner_width}} │\n"
    bot = f"└{'─' * (PREVIEW_BOX_WIDTH - 2)}┘\n"
    return [("", top + mid1 + mid2 + bot)]


def create_app(
    session: Session,
    table: ParameterTable,
    output_dir: Path,
    input: Input | None = None,
    output: Output | None = None,
) -> Application[None]:
    """Create prompt_toolkit Application instance."""
    state, kb = AppState(session, table, output_dir), KeyBindings()

    def _get_completer() -> WordCompleter | None:
        if state.state == "TYPE":
            return TYPE_COMPLETER
        if state.state == "UNIT":
            return UNIT_COMPLETER
        return None

    buffer = Buffer(
        completer=DynamicCompleter(_get_completer),
        complete_while_typing=True,
    )

    @kb.add("c-q")
    def _exit(event: KeyPressEvent) -> None:
        event.app.exit()

    @kb.add("c-s")
    def _save(_event: KeyPressEvent) -> None:
        if not (product := state.session.product_info):
            state.status = "No connection or product info yet."
            return
        slug = model_slug(product.model)
        module_path = output_dir / f"pyplumio/parameters/custom/{slug}.py"
        if module_path.is_file():
            prompt = (
                f"Overwrite existing {module_path.name}? Comments will be lost [y/N]: "
            )
            state._set_state("OVERWRITE", prompt, buffer)
        else:
            _save_files(state)

    @kb.add("escape", filter=has_completions)
    def _cancel_completion(_event: KeyPressEvent) -> None:
        buffer.cancel_completion()

    @kb.add("escape", filter=~has_completions)
    def _cancel(_event: KeyPressEvent) -> None:
        state.reset_wizard(buffer)
        state.status = "Cancelled."

    @kb.add("pageup")
    def _pageup(_event: KeyPressEvent) -> None:
        state.scroll_offset = max(0, state.scroll_offset - SCROLL_PAGE)

    @kb.add("pagedown")
    def _pagedown(_event: KeyPressEvent) -> None:
        state.scroll_offset = min(
            state.max_scroll_offset, state.scroll_offset + SCROLL_PAGE
        )

    @kb.add("up", filter=has_completions)
    def _up_completion(_event: KeyPressEvent) -> None:
        buffer.complete_previous()

    @kb.add("down", filter=has_completions)
    def _down_completion(_event: KeyPressEvent) -> None:
        buffer.complete_next()

    @kb.add("tab")
    def _tab(_event: KeyPressEvent) -> None:
        if buffer.complete_state:
            buffer.complete_next()
        else:
            buffer.start_completion(select_first=False)

    @kb.add("s-tab")
    def _s_tab(_event: KeyPressEvent) -> None:
        if buffer.complete_state:
            buffer.complete_previous()

    @kb.add("up", filter=~has_completions)
    def _up(_event: KeyPressEvent) -> None:
        state.scroll_offset = min(
            state.max_scroll_offset, max(0, state.scroll_offset - 1)
        )

    @kb.add("down", filter=~has_completions)
    def _down(_event: KeyPressEvent) -> None:
        state.scroll_offset = min(state.max_scroll_offset, state.scroll_offset + 1)

    @kb.add("enter")
    def _enter(_event: KeyPressEvent) -> None:
        state.dispatch_enter(buffer)

    body = HSplit(
        [
            Window(FormattedTextControl(lambda: _get_header_text(state)), height=2),
            Window(FormattedTextControl(lambda: _get_table_text(state))),
            Window(height=1),
            Window(
                FormattedTextControl(lambda: _get_preview_text(state, buffer)),
                height=4,
            ),
            Window(FormattedTextControl(lambda: f" {state.status}"), height=1),
            VSplit(
                [
                    Window(
                        FormattedTextControl(lambda: state.prompt),
                        dont_extend_width=True,
                    ),
                    Window(BufferControl(buffer=buffer)),
                ]
            ),
        ]
    )
    root = FloatContainer(
        content=body,
        floats=[
            Float(
                content=CompletionsMenu(max_height=6),
                xcursor=True,
                ycursor=True,
            )
        ],
    )
    app: Application[None] = Application(
        layout=Layout(root),
        key_bindings=kb,
        full_screen=True,
        input=input,
        output=output,
    )
    state.application = app
    app.state = state  # type: ignore[attr-defined]
    return app


async def run_app(args: argparse.Namespace) -> int:
    """Run PyPlumIO CLI application."""
    url = args.url or await prompt_connection_url()
    output_dir, table = Path(args.output), ParameterTable()
    app: Application[None] | None = None

    def on_update(
        parameters: Sequence[tuple[int, ParameterValues]], message: bytes
    ) -> None:
        table.update(parameters)
        if app:
            app.invalidate()

    session = Session(
        url=url, baudrate=args.baudrate, interval=args.interval, on_update=on_update
    )
    try:
        product_info = await session.connect()
        descriptions, overrides = load_custom_parameters(product_info.model, output_dir)
        for index, desc in descriptions.items():
            if isinstance(desc, (EcomaxNumberDescription, EcomaxSwitchDescription)):
                table.set_description(index, desc)
        table.overrides = overrides
        app = create_app(session, table, output_dir)
        await app.run_async()
    except (PyPlumIOError, ValueError) as err:
        print(f"Error: {err}", file=sys.stderr)  # noqa: T201
        return 1
    finally:
        await session.close()
    return 0


__all__ = (
    "AppState",
    "create_app",
    "prompt_connection_url",
    "run_app",
)
