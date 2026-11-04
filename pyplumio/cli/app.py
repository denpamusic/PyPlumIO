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
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.input import Input
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
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
UNIT_COMPLETER: Final = WordCompleter([u.name for u in UnitOfMeasurement] + ["%"])
TABLE_HEADER: Final = (
    "Index  Name                                  Value     Min       Max\n"
)
TABLE_SEPARATOR: Final = f"{'-' * 5}  {'-' * 36}  {'-' * 8}  {'-' * 8}  {'-' * 8}\n"


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
        self.state, self.prompt, self.status = "INDEX", "Index: ", ""
        self.scroll_offset, self.wizard_data, self.application = 0, {}, None

    def _set_state(
        self, state: str, prompt: str, buffer: Buffer, text: str = "", status: str = ""
    ) -> None:
        """Update wizard state and prompt buffer."""
        self.state, self.prompt, buffer.text, self.status = state, prompt, text, status

    def reset_wizard(self, buffer: Buffer) -> None:
        """Reset wizard back to index prompt."""
        self.state, self.prompt, buffer.text = "INDEX", "Index: ", ""
        self.wizard_data.clear()

    def step_index(self, text: str, buffer: Buffer) -> None:
        """Handle index step."""
        if text.isdigit() and (row := self.table.get(index := int(text))):
            self.wizard_data["index"] = index
            self._set_state("NAME", "Name: ", buffer, text=row.name)
            buffer.cursor_position = len(row.name)
        else:
            self._set_state(
                "INDEX", "Index: ", buffer, status="Index must exist in table."
            )

    def step_name(self, text: str, buffer: Buffer) -> None:
        """Handle name step."""
        if not NAME_REGEX.match(text):
            self.status = "Name must match ^[a-z][a-z0-9_]*$"
            return
        self.wizard_data["name"] = text
        self._set_state("TYPE", "Type [number/switch]: ", buffer)

    def step_type(self, text: str, buffer: Buffer) -> None:
        """Handle type step."""
        choice = text.lower() or "number"
        if choice == "switch":
            self.setup_preview(
                EcomaxSwitchDescription(name=self.wizard_data["name"]), buffer
            )
        elif choice == "number":
            self._set_state("STEP", "Step [1]: ", buffer)
        else:
            self.status = "Type must be 'number' or 'switch'"

    def step_step(self, text: str, buffer: Buffer) -> None:
        """Handle step step."""
        try:
            if (step := float(text) if text else 1.0) <= 0:
                raise ValueError
            self.wizard_data["step"] = int(step) if step.is_integer() else step
            self._set_state("OFFSET", "Offset [0]: ", buffer)
        except ValueError:
            self.status = "Step must be a positive number."

    def step_offset(self, text: str, buffer: Buffer) -> None:
        """Handle offset step."""
        try:
            self.wizard_data["offset"] = int(text) if text else 0
            self._set_state("UNIT", "Unit [none]: ", buffer)
        except ValueError:
            self.status = "Offset must be an integer."

    def step_unit(self, text: str, buffer: Buffer) -> None:
        """Handle unit step."""
        unit: UnitOfMeasurement | Literal["%"] | None = None
        if text == "%":
            unit = PERCENTAGE
        elif text and text.lower() != "none":
            with suppress(ValueError):
                unit = UnitOfMeasurement.__members__.get(
                    text.upper()
                ) or UnitOfMeasurement(text)
            if unit is None:
                self.status = "Unknown unit of measurement."
                return
        self.setup_preview(
            EcomaxNumberDescription(
                name=self.wizard_data["name"],
                step=self.wizard_data["step"],
                offset=self.wizard_data["offset"],
                unit_of_measurement=unit,
            ),
            buffer,
        )

    def setup_preview(
        self,
        description: EcomaxNumberDescription | EcomaxSwitchDescription,
        buffer: Buffer,
    ) -> None:
        """Set up preview prompt."""
        row = self.table.get(self.wizard_data["index"])
        preview = Row(0, row.values, description=description) if row else None
        val, min_val, max_val = (
            (preview.value, preview.min_value, preview.max_value)
            if preview
            else ("", "", "")
        )
        unit = getattr(description, "unit_of_measurement", None)
        u_str = f" {unit}" if unit else ""
        self.wizard_data["description"] = description
        prompt = (
            f"value={val}, min={min_val}, max={max_val}{u_str}. "
            "Does this match your device? [y/N]: "
        )
        self._set_state("PREVIEW", prompt, buffer)

    def step_preview(self, text: str, buffer: Buffer) -> None:
        """Handle preview step."""
        if text.lower() == "y":
            self.table.set_description(
                self.wizard_data["index"], self.wizard_data["description"]
            )
            self.status = f"Stored parameter {self.wizard_data['index']}."
        else:
            self.status = "Discarded."
        self.reset_wizard(buffer)

    def step_overwrite(self, text: str, buffer: Buffer) -> None:
        """Handle overwrite step."""
        if text.lower() == "y":
            _save_files(self)
        else:
            self.status = "Save cancelled."
        self.reset_wizard(buffer)

    def dispatch_enter(self, buffer: Buffer) -> None:
        """Dispatch enter key press to current step handler."""
        if handler := getattr(self, f"step_{self.state.lower()}", None):
            handler(buffer.text.strip(), buffer)


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
        state.status = f"Saved: {', '.join(str(path) for path in files)}"
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


def _get_table_text(state: AppState) -> StyleAndTextTuples:
    """Return formatted table text."""
    lines: StyleAndTextTuples = [("bold", TABLE_HEADER), ("bold", TABLE_SEPARATOR)]
    for row in state.table.rows()[state.scroll_offset : state.scroll_offset + 25]:
        val = f"{'*' if row.changed else ' '}{row.value}"
        lines.append(
            (
                "",
                f"{row.index:>5}  {row.name:<36}  {val:<8}  "
                f"{str(row.min_value):<8}  {str(row.max_value):<8}\n",
            )
        )
    return lines


def create_app(
    session: Session,
    table: ParameterTable,
    output_dir: Path,
    input: Input | None = None,
    output: Output | None = None,
) -> Application[None]:
    """Create prompt_toolkit Application instance."""
    state, kb = AppState(session, table, output_dir), KeyBindings()
    buffer = Buffer(
        completer=DynamicCompleter(
            lambda: UNIT_COMPLETER if state.state == "UNIT" else None
        )
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
            prompt = f"Overwrite existing {module_path}? Comments will be lost [y/N]: "
            state._set_state("OVERWRITE", prompt, buffer)
        else:
            _save_files(state)

    @kb.add("escape")
    def _cancel(_event: KeyPressEvent) -> None:
        state.reset_wizard(buffer)
        state.status = "Cancelled."

    @kb.add("pageup")
    def _pageup(_event: KeyPressEvent) -> None:
        state.scroll_offset = max(0, state.scroll_offset - 20)

    @kb.add("pagedown")
    def _pagedown(_event: KeyPressEvent) -> None:
        state.scroll_offset += 20

    @kb.add("enter")
    def _enter(_event: KeyPressEvent) -> None:
        state.dispatch_enter(buffer)

    root = HSplit(
        [
            Window(FormattedTextControl(lambda: _get_header_text(state)), height=2),
            Window(FormattedTextControl(lambda: _get_table_text(state))),
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
