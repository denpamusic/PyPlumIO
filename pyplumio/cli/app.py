"""Contains prompt_toolkit full-screen Application for PyPlumIO CLI."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from contextlib import suppress
from dataclasses import dataclass
from enum import StrEnum, unique
import logging
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
from pyplumio.parameters.ecomax import (
    PARAMETER_TYPES,
    EcomaxNumberDescription,
    EcomaxSwitchDescription,
)

DEFAULT_PORT: Final = 8899
MAX_PORT: Final = 65535
NAME_REGEX: Final = re.compile(r"^[a-z][a-z0-9_]*$")
PAGE_SIZE: Final = 25
SCROLL_PAGE: Final = 20
INDEX_PROMPT: Final = "Enter parameter index to edit: "
UNIT_WORDS: Final = tuple(unit.value for unit in UnitOfMeasurement) + (PERCENTAGE,)
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
        **{
            unit.value: unit.name.replace("_", " ").lower()
            for unit in UnitOfMeasurement
        },
        PERCENTAGE: "percentage",
    },
)
TYPE_COMPLETER: Final = WordCompleter(["number", "switch"])
TABLE_HEADER: Final = (
    "Index  Name                                  Value       Min         Max\n"
)
TABLE_SEPARATOR: Final = f"{'-' * 5}  {'-' * 36}  {'-' * 10}  {'-' * 10}  {'-' * 10}\n"
PREVIEW_BOX_WIDTH: Final = 78


@unique
class AppStep(StrEnum):
    """Represents application steps."""

    INDEX = "index"
    NAME = "name"
    CONFIRM_STANDARD_NAME = "confirm_standard_name"
    TYPE = "type"
    OFFSET = "offset"
    STEP = "step"
    UNIT = "unit"
    CONFIRM = "confirm"
    OVERWRITE = "overwrite"


@dataclass(slots=True)
class AppData:
    """Holds working data for the application."""

    index: int | None = None
    name: str | None = None
    default_type: str = "number"
    offset: int = 0
    step: float | int = 1
    description: EcomaxNumberDescription | EcomaxSwitchDescription | None = None

    def reset(self) -> None:
        """Reset app data fields to defaults."""
        self.index = None
        self.name = None
        self.default_type = "number"
        self.offset = 0
        self.step = 1
        self.description = None


async def prompt_connection_url(
    prompt_session: PromptSession[str] | None = None,
) -> str:
    """Prompt user for connection details and return the connection URL."""
    session = prompt_session or PromptSession()
    type_validator = Validator.from_callable(
        lambda text: text.strip().lower() in ("tcp", "serial"),
        error_message="Must be 'tcp' or 'serial'",
    )
    connection_type = (
        (
            await session.prompt_async(
                "Connection type (tcp/serial): ",
                completer=WordCompleter(["tcp", "serial"]),
                validator=type_validator,
            )
        )
        .strip()
        .lower()
    )
    if connection_type == "tcp":
        host_validator = Validator.from_callable(
            lambda text: bool(text.strip()), error_message="Host cannot be empty"
        )
        host = (await session.prompt_async("Host: ", validator=host_validator)).strip()
        port_validator = Validator.from_callable(
            lambda text: (
                not text.strip()
                or (text.strip().isdigit() and 1 <= int(text) <= MAX_PORT)
            ),
            error_message=f"Port must be 1-{MAX_PORT}",
        )
        port = (
            await session.prompt_async(
                f"Port [{DEFAULT_PORT}]: ", validator=port_validator
            )
        ).strip()
        return f"socket://{host}:{int(port) if port else DEFAULT_PORT}"

    url_validator = Validator.from_callable(
        lambda text: bool(text.strip()), error_message="URL cannot be empty"
    )
    return (
        await session.prompt_async(
            "Device URL (e.g. /dev/ttyUSB0, COM3): ", validator=url_validator
        )
    ).strip()


class AppState:
    """Represents application UI and state."""

    __slots__ = (
        "application",
        "data",
        "output_dir",
        "prompt",
        "scroll_offset",
        "session",
        "status",
        "step",
        "table",
        "_handlers",
    )

    application: Application[None] | None
    data: AppData
    output_dir: Path
    prompt: str
    scroll_offset: int
    session: Session
    status: str
    step: AppStep
    table: ParameterTable
    _handlers: dict[AppStep, Callable[[str, Buffer], None]]

    def __init__(
        self, session: Session, table: ParameterTable, output_dir: Path
    ) -> None:
        """Initialize application state."""
        self.session = session
        self.table = table
        self.output_dir = output_dir
        self.step = AppStep.INDEX
        self.prompt = INDEX_PROMPT
        self.status = ""
        self.scroll_offset = 0
        self.data = AppData()
        self.application = None
        self._handlers = {
            AppStep.INDEX: self.step_index,
            AppStep.NAME: self.step_name,
            AppStep.CONFIRM_STANDARD_NAME: self.step_confirm_standard_name,
            AppStep.TYPE: self.step_type,
            AppStep.OFFSET: self.step_offset,
            AppStep.STEP: self.step_step,
            AppStep.UNIT: self.step_unit,
            AppStep.CONFIRM: self.step_confirm,
            AppStep.OVERWRITE: self.step_overwrite,
        }

    @property
    def state(self) -> str:
        """Return step value string for compatibility."""
        return self.step.value

    @property
    def max_scroll_offset(self) -> int:
        """Return maximum scroll offset."""
        return max(0, len(self.table) - PAGE_SIZE)

    def set_step(
        self,
        step: AppStep,
        prompt: str,
        buffer: Buffer,
        text: str = "",
        status: str = "",
    ) -> None:
        """Update app step and prompt buffer."""
        self.step = step
        self.prompt = prompt
        buffer.text = text
        self.status = status

    def reset_app(self, buffer: Buffer, status: str | None = None) -> None:
        """Reset app back to index prompt."""
        self.table.unfreeze()
        self.set_step(
            AppStep.INDEX,
            INDEX_PROMPT,
            buffer,
            status=self.status if status is None else status,
        )
        self.data.reset()

    def step_index(self, text: str, buffer: Buffer) -> None:
        """Handle index step."""
        if text.isdigit() and (row := self.table.get(index := int(text))):
            self.table.clear_changed(index)
            self.table.freeze()
            self.data.index = index
            self.set_step(AppStep.NAME, "Name: ", buffer, text=row.name)
            buffer.cursor_position = len(row.name)
        else:
            self.set_step(
                AppStep.INDEX,
                INDEX_PROMPT,
                buffer,
                status="Index must exist in table.",
            )

    def _advance_to_type(self, buffer: Buffer) -> None:
        """Advance app to type selection step."""
        row = self.table.get(self.data.index if self.data.index is not None else -1)
        is_switch = (
            row is not None and row.values.min_value == 0 and row.values.max_value == 1
        )
        default_type = "switch" if is_switch else "number"
        self.data.default_type = default_type
        self.set_step(
            AppStep.TYPE,
            f"Parameter type (number, switch) [{default_type}]: ",
            buffer,
        )

    def step_name(self, text: str, buffer: Buffer) -> None:
        """Handle name step."""
        if not NAME_REGEX.match(text):
            self.status = (
                "Name must start with a lowercase letter and contain only "
                "lowercase letters, numbers, and underscores."
            )
            return

        for index, description in self.table.descriptions.items():
            if index != self.data.index and description.name == text:
                self.status = f"Name '{text}' is already used by index {index}."
                return

        self.data.name = text

        product_info = self.session.product_info
        if product_info and (
            standard_parameters := PARAMETER_TYPES.get(product_info.type)
        ):
            if any(param.name == text for param in standard_parameters):
                prompt = (
                    f"'{text}' is also a standard parameter; both will share one "
                    "event name. Continue? [y/N]: "
                )
                self.set_step(AppStep.CONFIRM_STANDARD_NAME, prompt, buffer)
                return

        self._advance_to_type(buffer)

    def step_confirm_standard_name(self, text: str, buffer: Buffer) -> None:
        """Handle confirm standard parameter name step."""
        if text.lower() in ("y", "yes"):
            self._advance_to_type(buffer)
        else:
            self.set_step(
                AppStep.NAME,
                "Name: ",
                buffer,
                text=self.data.name or "",
            )
            buffer.cursor_position = len(buffer.text)

    def step_type(self, text: str, buffer: Buffer) -> None:
        """Handle type step."""
        choice = text.lower() or self.data.default_type
        if choice == "switch":
            self.setup_confirm(
                EcomaxSwitchDescription(name=self.data.name or ""), buffer
            )
        elif choice == "number":
            self.set_step(AppStep.OFFSET, "Offset [0]: ", buffer)
        else:
            self.status = "Type must be 'number' or 'switch'."

    def step_offset(self, text: str, buffer: Buffer) -> None:
        """Handle offset step."""
        try:
            self.data.offset = int(text) if text else 0
            self.set_step(AppStep.STEP, "Step [1]: ", buffer)
        except ValueError:
            self.status = "Offset must be an integer."

    def step_step(self, text: str, buffer: Buffer) -> None:
        """Handle step step."""
        try:
            if (step := float(text) if text else 1.0) <= 0:
                raise ValueError
            self.data.step = int(step) if step.is_integer() else step
            units_display = ", ".join(UNIT_WORDS)
            self.set_step(
                AppStep.UNIT,
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
                name=self.data.name or "",
                step=self.data.step,
                offset=self.data.offset,
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
        row = self.table.get(self.data.index if self.data.index is not None else -1)
        preview = Row(0, row.values, description=description) if row else None
        value, min_value, max_value = (
            (preview.value, preview.min_value, preview.max_value)
            if preview
            else ("", "", "")
        )
        unit = getattr(description, "unit_of_measurement", None)
        unit_string = f" {unit}" if unit else ""
        self.data.description = description
        name = self.data.name
        prompt = (
            f"{name}: {value}{unit_string} ({min_value}-{max_value}{unit_string}). "
            "Does this match your device? [y/N]: "
        )
        self.set_step(AppStep.CONFIRM, prompt, buffer)

    def step_confirm(self, text: str, buffer: Buffer) -> None:
        """Handle confirm step."""
        if text.lower() in ("y", "yes") and self.data.index is not None:
            self.table.set_description(self.data.index, self.data.description)
            status = f"Stored parameter {self.data.index}."
        else:
            status = "Discarded."
        self.reset_app(buffer, status=status)

    def step_overwrite(self, text: str, buffer: Buffer) -> None:
        """Handle overwrite step."""
        if text.lower() in ("y", "yes"):
            _save_files(self)
            status = self.status
        else:
            status = "Save cancelled."
        self.reset_app(buffer, status=status)

    def dispatch_enter(self, buffer: Buffer) -> None:
        """Dispatch enter key press to current step handler."""
        if handler := self._handlers.get(self.step):
            handler(buffer.text.strip(), buffer)


class StatusLogHandler(logging.Handler):
    """Log handler routing warning and higher logs to app status."""

    __slots__ = ("_state",)

    _state: AppState

    def __init__(self, state: AppState) -> None:
        """Initialize the status log handler."""
        super().__init__(level=logging.WARNING)
        self._state = state

    def emit(self, record: logging.LogRecord) -> None:
        """Emit log message to app status."""
        self._state.status = self.format(record)
        if self._state.application:
            self._state.application.invalidate()


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
    product_info = state.session.product_info
    frame_message = state.session.last_frame_message
    parameters = state.session.last_parameters
    if not product_info or not frame_message or not parameters:
        state.status = "Error: no data received yet."
        return
    try:
        files = generate_all_files(
            product_info,
            state.table.descriptions,
            state.table.overrides,
            frame_message,
            parameters,
            state.output_dir,
        )
        write_files(files)
        state.status = f"Files saved to {state.output_dir}."
    except (OSError, ValueError) as err:
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
    return f"{value} {unit}"


def _get_table_text(state: AppState) -> StyleAndTextTuples:
    """Return formatted table text."""
    lines: StyleAndTextTuples = [("bold", TABLE_HEADER), ("bold", TABLE_SEPARATOR)]
    offset = min(state.scroll_offset, state.max_scroll_offset)
    for row in state.table.rows()[offset : offset + PAGE_SIZE]:
        value = _format_value_with_unit(row.value, row.description)
        min_value = _format_value_with_unit(row.min_value, row.description)
        max_value = _format_value_with_unit(row.max_value, row.description)
        row_text = (
            f"{row.index:>5}  {row.name:<36}  {value:<10}  {min_value:<10}  "
            f"{max_value:<10}\n"
        )
        lines.append(("reverse", row_text) if row.changed else ("", row_text))
    return lines


def _format_field(label: str, value: Any, active: bool) -> str:
    """Format a single preview field, bracketing it when active."""
    text = f"{label}: {value}"
    return f"[{text}]" if active else text


def _resolve_preview_row(state: AppState, text: str) -> Row | None:
    """Return the Row currently being previewed."""
    if state.data.index is not None:
        return state.table.get(state.data.index)
    if state.step == AppStep.INDEX and text.isdigit():
        return state.table.get(int(text))
    return None


def _resolve_live_number_params(
    state: AppState, text: str
) -> tuple[int, float | int, UnitOfMeasurement | Literal["%"] | None]:
    """Return live (offset, step, unit) from app data and current buffer."""
    offset: int = state.data.offset
    if state.step == AppStep.OFFSET and text:
        with suppress(ValueError):
            offset = int(text)

    step: float | int = state.data.step
    if state.step == AppStep.STEP and text:
        with suppress(ValueError):
            if (parsed := float(text)) > 0:
                step = int(parsed) if parsed.is_integer() else parsed

    unit: UnitOfMeasurement | Literal["%"] | None = None
    if state.step == AppStep.UNIT:
        parsed_unit = _parse_unit(text)
        unit = None if parsed_unit is False else parsed_unit
    return offset, step, unit


def _build_live_description(
    state: AppState, row: Row, text: str
) -> EcomaxNumberDescription | EcomaxSwitchDescription | None:
    """Build transient description for live preview."""
    if state.step == AppStep.INDEX:
        return row.description
    if state.step in (AppStep.CONFIRM, AppStep.OVERWRITE):
        return state.data.description or row.description
    name = (
        text
        if state.step == AppStep.NAME
        else state.data.name
        if state.step == AppStep.CONFIRM_STANDARD_NAME
        else state.data.name or row.name
    )
    name = name or "<unnamed>"
    if (
        state.step in (AppStep.NAME, AppStep.CONFIRM_STANDARD_NAME)
        and isinstance(row.description, EcomaxSwitchDescription)
        or state.step == AppStep.TYPE
        and (text.lower() or state.data.default_type) == "switch"
    ):
        return EcomaxSwitchDescription(name=name)
    if state.step in (
        AppStep.NAME,
        AppStep.CONFIRM_STANDARD_NAME,
        AppStep.TYPE,
    ):
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
        message = (
            "Enter a parameter index below to preview raw values and live calculations."
        )
        mid1 = f"│ {message:<{inner_width}} │\n"
        mid2 = f"│ {'':<{inner_width}} │\n"
        bot = f"└{'─' * (PREVIEW_BOX_WIDTH - 2)}┘\n"
        return [("", top + mid1 + mid2 + bot)]

    description = _build_live_description(state, row, text)
    preview = Row(row.index, row.values, description=description)
    is_switch = isinstance(description, EcomaxSwitchDescription)
    type_string = "switch" if is_switch else "number"
    offset_val = getattr(description, "offset", 0)
    step_val = getattr(description, "step", 1)
    unit_val = getattr(description, "unit_of_measurement", None)
    unit_string = f" {unit_val}" if unit_val else ""

    fields = [
        _format_field(
            "Name",
            preview.name or "<unnamed>",
            state.step in (AppStep.NAME, AppStep.CONFIRM_STANDARD_NAME),
        ),
        _format_field("Type", type_string, state.step == AppStep.TYPE),
    ]
    if not is_switch:
        fields.extend(
            [
                _format_field("Offset", offset_val, state.step == AppStep.OFFSET),
                _format_field("Step", step_val, state.step == AppStep.STEP),
                _format_field("Unit", unit_val or "none", state.step == AppStep.UNIT),
            ]
        )
    line1_content = "  ".join(fields)[:inner_width]
    raw = row.values
    preview_range = f"{preview.min_value}-{preview.max_value}{unit_string}"
    line2_content = (
        f"Raw: {raw.value} (min: {raw.min_value}, max: {raw.max_value})  ──►  "
        f"Preview: {preview.value}{unit_string} ({preview_range})"
    )[:inner_width]
    header_title = f"─ Live Preview (Index #{row.index}) "
    top = f"┌{header_title}{'─' * max(0, PREVIEW_BOX_WIDTH - 2 - len(header_title))}┐\n"
    mid1 = f"│ {line1_content:<{inner_width}} │\n"
    mid2 = f"│ {line2_content:<{inner_width}} │\n"
    bot = f"└{'─' * (PREVIEW_BOX_WIDTH - 2)}┘\n"
    return [("", top + mid1 + mid2 + bot)]


def _get_completer(state: AppState) -> WordCompleter | None:
    """Return completer for current app step."""
    if state.step == AppStep.TYPE:
        return TYPE_COMPLETER
    if state.step == AppStep.UNIT:
        return UNIT_COMPLETER
    return None


def _create_key_bindings(
    state: AppState, buffer: Buffer, output_dir: Path
) -> KeyBindings:
    """Create key bindings for application."""
    key_bindings = KeyBindings()

    @key_bindings.add("c-q")
    def _exit(event: KeyPressEvent) -> None:
        event.app.exit()

    @key_bindings.add("c-s")
    def _save(_event: KeyPressEvent) -> None:
        if not (product := state.session.product_info):
            state.status = "No connection or product info yet."
            return
        mapped_descriptions = [
            description
            for description in state.table.descriptions.values()
            if isinstance(
                description, (EcomaxNumberDescription, EcomaxSwitchDescription)
            )
        ]
        if not mapped_descriptions:
            state.status = "Nothing to save: map at least one parameter first."
            return
        slug = model_slug(product.model)
        module_path = output_dir / f"pyplumio/parameters/custom/{slug}.py"
        if module_path.is_file():
            prompt = (
                f"Overwrite existing {module_path.name}? Comments will be lost [y/N]: "
            )
            state.set_step(AppStep.OVERWRITE, prompt, buffer)
        else:
            _save_files(state)

    @key_bindings.add("escape", filter=has_completions)
    def _cancel_completion(_event: KeyPressEvent) -> None:
        buffer.cancel_completion()

    @key_bindings.add("escape", filter=~has_completions)
    def _cancel(_event: KeyPressEvent) -> None:
        state.reset_app(buffer)
        state.status = "Cancelled."

    @key_bindings.add("pageup")
    def _pageup(_event: KeyPressEvent) -> None:
        state.scroll_offset = max(0, state.scroll_offset - SCROLL_PAGE)

    @key_bindings.add("pagedown")
    def _pagedown(_event: KeyPressEvent) -> None:
        state.scroll_offset = min(
            state.max_scroll_offset, state.scroll_offset + SCROLL_PAGE
        )

    @key_bindings.add("up", filter=has_completions)
    def _up_completion(_event: KeyPressEvent) -> None:
        buffer.complete_previous()

    @key_bindings.add("down", filter=has_completions)
    def _down_completion(_event: KeyPressEvent) -> None:
        buffer.complete_next()

    @key_bindings.add("tab")
    def _tab(_event: KeyPressEvent) -> None:
        if buffer.complete_state:
            buffer.complete_next()
        else:
            buffer.start_completion(select_first=False)

    @key_bindings.add("s-tab")
    def _s_tab(_event: KeyPressEvent) -> None:
        if buffer.complete_state:
            buffer.complete_previous()

    @key_bindings.add("up", filter=~has_completions)
    def _up(_event: KeyPressEvent) -> None:
        state.scroll_offset = min(
            state.max_scroll_offset, max(0, state.scroll_offset - 1)
        )

    @key_bindings.add("down", filter=~has_completions)
    def _down(_event: KeyPressEvent) -> None:
        state.scroll_offset = min(state.max_scroll_offset, state.scroll_offset + 1)

    @key_bindings.add("enter")
    def _enter(_event: KeyPressEvent) -> None:
        state.dispatch_enter(buffer)

    return key_bindings


def create_app(
    session: Session,
    table: ParameterTable,
    output_dir: Path,
    input: Input | None = None,
    output: Output | None = None,
) -> tuple[Application[None], AppState]:
    """Create prompt_toolkit Application instance and AppState."""
    state = AppState(session, table, output_dir)
    buffer = Buffer(
        completer=DynamicCompleter(lambda: _get_completer(state)),
        complete_while_typing=True,
    )
    key_bindings = _create_key_bindings(state, buffer, output_dir)
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
    application: Application[None] = Application(
        layout=Layout(root),
        key_bindings=key_bindings,
        full_screen=True,
        input=input,
        output=output,
    )
    state.application = application
    return application, state


async def run_app(args: argparse.Namespace) -> int:
    """Run PyPlumIO CLI application."""
    url = args.url or await prompt_connection_url()
    output_dir, table = Path(args.output), ParameterTable()
    app: Application[None] | None = None
    state: AppState | None = None

    def on_update(
        parameters: Sequence[tuple[int, ParameterValues]], message: bytes
    ) -> None:
        table.update(parameters)
        if app:
            app.invalidate()

    def on_disconnect(reason: str) -> None:
        if state:
            state.status = (
                f"Connection lost: {reason}. "
                "Ctrl+S still saves the last received frame, Ctrl+Q quits."
            )
        if app:
            app.invalidate()

    session = Session(
        url=url,
        baudrate=args.baudrate,
        interval=args.interval,
        on_update=on_update,
        on_disconnect=on_disconnect,
    )
    try:
        product_info = await session.connect()
        descriptions, overrides = load_custom_parameters(product_info.model, output_dir)
        for index, description in descriptions.items():
            if isinstance(
                description, (EcomaxNumberDescription, EcomaxSwitchDescription)
            ):
                table.set_description(index, description)
        table.overrides = overrides
        app, state = create_app(session, table, output_dir)
        status_handler = StatusLogHandler(state)
        pyplumio_logger = logging.getLogger("pyplumio")
        original_handlers = pyplumio_logger.handlers[:]
        original_propagate = pyplumio_logger.propagate
        pyplumio_logger.handlers = [status_handler]
        pyplumio_logger.propagate = False
        try:
            await app.run_async()
        finally:
            pyplumio_logger.handlers = original_handlers
            pyplumio_logger.propagate = original_propagate
    except (PyPlumIOError, ValueError) as err:
        sys.stderr.write(f"Error: {err}\n")
        return 1
    finally:
        await session.close()
    return 0


__all__ = (
    "AppData",
    "AppState",
    "AppStep",
    "create_app",
    "prompt_connection_url",
    "run_app",
)
