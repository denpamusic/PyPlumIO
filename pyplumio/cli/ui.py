"""Contains prompt_toolkit UI layout and key bindings for PyPlumIO CLI."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import replace
from pathlib import Path
from typing import Any, Final

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

from pyplumio.cli.model import ParameterTable, Row
from pyplumio.cli.session import Session
from pyplumio.cli.state import (
    PAGE_SIZE,
    UNIT_ALIASES,
    UNIT_WORDS,
    UNNAMED,
    AppState,
    AppStep,
    _format_preview_value,
    _format_value_with_unit,
    _ParameterType,
    _parse_step,
)
from pyplumio.const import PERCENTAGE, UnitOfMeasurement
from pyplumio.parameters.ecomax import (
    PARAMETER_TYPES,
    EcomaxNumberDescription,
    EcomaxParameterDescription,
    EcomaxSwitchDescription,
)

SCROLL_SIZE: Final = 20
PREVIEW_BOX_WIDTH: Final = 78
TABLE_HEADER: Final = (
    "Index  Name                                  Value       Min         Max\n"
)
TABLE_SEPARATOR: Final = f"{'-' * 5}  {'-' * 36}  {'-' * 10}  {'-' * 10}  {'-' * 10}\n"

TYPE_COMPLETER: Final = WordCompleter(list(_ParameterType))
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


def _get_header_text(state: AppState) -> StyleAndTextTuples:
    """Return formatted header text."""
    product_info = state.session.product_info
    last_update = state.session.last_update_time
    model, product_id = (
        (product_info.model, product_info.id) if product_info else ("Unknown", 0)
    )
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


def _get_preview_row(state: AppState, text: str) -> Row | None:
    """Return the Row currently being previewed."""
    if state.data.index is not None:
        return state.table.get(state.data.index)

    if state.step == AppStep.INDEX and text.isdigit():
        return state.table.get(int(text))

    return None


def _create_live_description(
    state: AppState, row: Row, text: str
) -> EcomaxParameterDescription:
    """Create transient description for live preview."""
    name = (text if state.step == AppStep.NAME else state.data.name) or UNNAMED
    number = EcomaxNumberDescription(
        name=name,
        offset=state.data.offset,
        step=state.data.step,
        unit_of_measurement=state.data.unit,
    )
    description: EcomaxParameterDescription = number
    match state.step:
        case (
            AppStep.INDEX
            | AppStep.COMMENT
            | AppStep.CONFIRM
            | AppStep.ZIP
            | AppStep.OVERWRITE
        ):
            description = state.data.description or row.description or number
        case AppStep.NAME if isinstance(row.description, EcomaxSwitchDescription):
            description = EcomaxSwitchDescription(name=name)
        case AppStep.TYPE if (
            text.lower() or state.data.default_type
        ) == _ParameterType.SWITCH:
            description = EcomaxSwitchDescription(name=name)
        case AppStep.OFFSET:
            with suppress(ValueError):
                description = replace(number, offset=int(text))
        case AppStep.STEP:
            with suppress(ValueError):
                description = replace(
                    number, step=_parse_step(text, default=state.data.step)
                )
        case AppStep.UNIT if text and (key := text.lower()) in UNIT_ALIASES:
            description = replace(number, unit_of_measurement=UNIT_ALIASES[key])

    return description


def _format_preview_box(title: str, line1: str = "", line2: str = "") -> str:
    """Return 4-line preview box with a title and two content lines."""
    inner_width = PREVIEW_BOX_WIDTH - 4
    border_width = PREVIEW_BOX_WIDTH - 2
    title = f"─ {title} "
    return (
        f"┌{title}{'─' * max(0, border_width - len(title))}┐\n"
        f"│ {line1[:inner_width]:<{inner_width}} │\n"
        f"│ {line2[:inner_width]:<{inner_width}} │\n"
        f"└{'─' * border_width}┘\n"
    )


def _format_raw_value(row: Row) -> str:
    """Format raw value."""
    value, min_value, max_value = (
        row.values.value,
        row.values.min_value,
        row.values.max_value,
    )
    return f"{value} (min: {min_value}, max: {max_value})"


def _get_preview_text(state: AppState, buffer: Buffer) -> StyleAndTextTuples:
    """Return formatted 4-line live preview box."""
    text = buffer.text.strip()
    row = _get_preview_row(state, text)
    if row is None:
        return [
            (
                "",
                _format_preview_box(
                    "Live Preview",
                    "Enter a parameter index below to preview raw values and live "
                    "calculations.",
                ),
            )
        ]

    description = _create_live_description(state, row, text)
    preview = Row(row.index, row.values, description=description)
    parameter_type = (
        _ParameterType.NUMBER
        if isinstance(description, EcomaxNumberDescription)
        else _ParameterType.SWITCH
    )
    fields: list[str] = [
        _format_field("Name", preview.name, state.step == AppStep.NAME),
        _format_field("Type", parameter_type, state.step == AppStep.TYPE),
    ]
    if isinstance(description, EcomaxNumberDescription):
        fields.extend(
            [
                _format_field(
                    "Offset", description.offset, state.step == AppStep.OFFSET
                ),
                _format_field("Step", description.step, state.step == AppStep.STEP),
                _format_field(
                    "Unit",
                    description.unit_of_measurement or "none",
                    state.step == AppStep.UNIT,
                ),
            ]
        )

    return [
        (
            "",
            _format_preview_box(
                f"Live Preview (Index #{row.index})",
                "  ".join(fields),
                (
                    f"Raw: {_format_raw_value(row)}  ──►  "
                    f"Preview: {_format_preview_value(preview)}"
                ),
            ),
        )
    ]


def _get_name_completer(state: AppState) -> WordCompleter | None:
    """Return WordCompleter for unused standard parameter names."""
    if not (product_info := state.session.product_info):
        return None

    used_names = {
        description.name
        for index, description in state.table.descriptions.items()
        if index != state.data.index
    }

    available_names = [
        parameter.name
        for parameter in PARAMETER_TYPES.get(product_info.type, [])
        if parameter.name not in used_names
    ]

    return WordCompleter(available_names, match_middle=True)


def _get_completer(state: AppState) -> WordCompleter | None:
    """Return active completer for the current application step."""
    completer: WordCompleter | None = None

    match state.step:
        case AppStep.NAME:
            completer = _get_name_completer(state)
        case AppStep.TYPE:
            completer = TYPE_COMPLETER
        case AppStep.UNIT:
            completer = UNIT_COMPLETER

    return completer


def _create_key_bindings(state: AppState, buffer: Buffer) -> KeyBindings:
    """Create key bindings for application."""
    key_bindings = KeyBindings()

    @key_bindings.add("c-q")
    def _exit(event: KeyPressEvent) -> None:
        event.app.exit()

    @key_bindings.add("c-s")
    def _save(_event: KeyPressEvent) -> None:
        state.start_save(buffer)

    @key_bindings.add("escape", filter=has_completions)
    def _cancel_completion(_event: KeyPressEvent) -> None:
        buffer.cancel_completion()

    @key_bindings.add("escape", filter=~has_completions)
    def _cancel(_event: KeyPressEvent) -> None:
        state.reset_app(buffer)
        state.status = "Cancelled."

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

    def _scroll(delta: int) -> None:
        """Scroll by delta offset."""
        state.scroll_offset = min(
            state.max_scroll_offset, max(0, state.scroll_offset + delta)
        )

    @key_bindings.add("pageup")
    def _pageup(_event: KeyPressEvent) -> None:
        _scroll(delta=-SCROLL_SIZE)

    @key_bindings.add("pagedown")
    def _pagedown(_event: KeyPressEvent) -> None:
        _scroll(delta=SCROLL_SIZE)

    @key_bindings.add("up", filter=~has_completions)
    def _up(_event: KeyPressEvent) -> None:
        _scroll(delta=-1)

    @key_bindings.add("down", filter=~has_completions)
    def _down(_event: KeyPressEvent) -> None:
        _scroll(delta=1)

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
    *,
    zip_output: bool = False,
) -> tuple[Application[None], AppState]:
    """Create prompt_toolkit Application instance and AppState."""
    state = AppState(session, table, output_dir, zip_output=zip_output)
    buffer = Buffer(
        completer=DynamicCompleter(lambda: _get_completer(state)),
        complete_while_typing=True,
    )
    key_bindings = _create_key_bindings(state, buffer)
    body = HSplit(
        [
            Window(FormattedTextControl(lambda: _get_header_text(state)), height=2),
            Window(FormattedTextControl(lambda: _get_table_text(state))),
            Window(height=1),
            Window(
                FormattedTextControl(lambda: _get_preview_text(state, buffer)),
                height=4,
            ),
            Window(
                FormattedTextControl(lambda: f" {state.status}"),
                wrap_lines=True,
                dont_extend_height=True,
            ),
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


__all__ = ("create_app",)
