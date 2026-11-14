"""Contains application state and wizard steps for PyPlumIO CLI."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum, unique
from pathlib import Path
import re
from typing import Any, Final, Literal, cast

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer

from pyplumio.cli.codegen import (
    custom_module_path,
    generate_all_files,
    write_files,
    write_zip,
    zip_archive_path,
)
from pyplumio.cli.model import ParameterTable, Row
from pyplumio.cli.session import Session
from pyplumio.const import PERCENTAGE, UnitOfMeasurement
from pyplumio.parameters.custom import model_slug
from pyplumio.parameters.ecomax import (
    PARAMETER_TYPES,
    EcomaxNumberDescription,
    EcomaxParameterDescription,
    EcomaxSwitchDescription,
)


@unique
class AppStep(StrEnum):
    """Contains application steps."""

    INDEX = "index"
    NAME = "name"
    TYPE = "type"
    OFFSET = "offset"
    STEP = "step"
    UNIT = "unit"
    COMMENT = "comment"
    CONFIRM = "confirm"
    ZIP = "zip"
    OVERWRITE = "overwrite"


@unique
class _ParameterType(StrEnum):
    """Contains parameter types."""

    NUMBER = "number"
    SWITCH = "switch"


NAME_REGEX: Final = re.compile(r"^[a-z][a-z0-9_]*$")
UNNAMED: Final = "<unnamed>"
AVAILABLE_TYPES: Final = ", ".join(_ParameterType)
UNIT_WORDS: Final = tuple(unit.value for unit in UnitOfMeasurement) + (PERCENTAGE,)
UNIT_ALIASES: Final[dict[str, UnitOfMeasurement | Literal["%"] | None]] = {
    "": None,
    "none": None,
    "%": PERCENTAGE,
    "percent": PERCENTAGE,
    "percentage": PERCENTAGE,
    "c": UnitOfMeasurement.CELSIUS,
    "degc": UnitOfMeasurement.CELSIUS,
    "d": UnitOfMeasurement.DAYS,
    "day": UnitOfMeasurement.DAYS,
    "sec": UnitOfMeasurement.SECONDS,
    "second": UnitOfMeasurement.SECONDS,
    "minute": UnitOfMeasurement.MINUTES,
    **{unit.value.lower(): unit for unit in UnitOfMeasurement},
    **{unit.name.lower(): unit for unit in UnitOfMeasurement},
}
AVAILABLE_UNITS: Final = ", ".join(UNIT_WORDS)

PAGE_SIZE: Final = 25
INDEX_PROMPT: Final = "Enter parameter index to edit: "
NAME_PROMPT: Final = "Name: "
COMMENT_PROMPT: Final = "Comment (leave empty for none): "
ZIP_PROMPT: Final = "Save as a ZIP archive? [y/N]: "


def _normalize_number(value: float) -> float | int:
    """Return int if float has no fractional part, otherwise float."""
    return int(value) if float(value).is_integer() else value


def _is_yes(text: str) -> bool:
    """Return True if answer is yes."""
    return text.lower() in ("y", "yes")


def _parse_step(text: str, default: float | int = 1) -> float | int:
    """Parse positive step value from user input."""
    if (step := float(text) if text else float(default)) <= 0:
        raise ValueError

    return _normalize_number(step)


def _format_value_with_unit(
    value: Any, description: EcomaxParameterDescription | None
) -> str:
    """Format parameter value with unit of measurement if available."""
    if (
        isinstance(description, EcomaxNumberDescription)
        and description.unit_of_measurement
    ):
        return f"{value} {description.unit_of_measurement}"

    return str(value)


def _format_preview_value(preview: Row) -> str:
    """Format preview value."""
    value, min_value, max_value = preview.value, preview.min_value, preview.max_value
    value_string = _format_value_with_unit(value, preview.description)
    range_string = _format_value_with_unit(
        f"{min_value}-{max_value}", preview.description
    )
    return f"{value_string} ({range_string})"


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
            comments=state.table.comments,
        )
        if state.data.save_as_zip:
            zip_path = zip_archive_path(
                state.output_dir, model_slug(product_info.model)
            )
            write_zip(zip_path, files, state.output_dir)
            state.status = f"Files saved to {zip_path}."
        else:
            write_files(files)
            state.status = f"Files saved to {state.output_dir}."

    except (OSError, ValueError) as err:
        state.status = f"Error saving files: {err}"


@dataclass(slots=True)
class AppData:
    """Represents working data for the application."""

    index: int | None = None
    name: str = ""
    default_type: _ParameterType = _ParameterType.NUMBER
    offset: int = 0
    step: float | int = 1
    unit: UnitOfMeasurement | Literal["%"] | None = None
    description: EcomaxParameterDescription | None = None
    comment: str = ""
    save_as_zip: bool = False

    def apply_template(
        self,
        description: EcomaxParameterDescription | None,
        *,
        parameter_type: _ParameterType = _ParameterType.NUMBER,
    ) -> None:
        """Apply template defaults from a parameter description."""
        self.offset = 0
        self.step = 1
        self.unit = None
        self.default_type = parameter_type

        if isinstance(description, EcomaxSwitchDescription):
            self.default_type = _ParameterType.SWITCH
            return

        if isinstance(description, EcomaxNumberDescription):
            self.default_type = _ParameterType.NUMBER
            self.offset = description.offset
            self.step = _normalize_number(description.step)
            self.unit = description.unit_of_measurement


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
        "zip_output",
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
    zip_output: bool

    def __init__(
        self,
        session: Session,
        table: ParameterTable,
        output_dir: Path,
        *,
        zip_output: bool = False,
    ) -> None:
        """Initialize application state."""
        self.session = session
        self.table = table
        self.output_dir = output_dir
        self.zip_output = zip_output
        self.step = AppStep.INDEX
        self.prompt = INDEX_PROMPT
        self.status = ""
        self.scroll_offset = 0
        self.data = AppData()
        self.application = None

    def reset_app(self, buffer: Buffer, status: str | None = None) -> None:
        """Reset app back to index prompt."""
        if not status:
            status = self.status

        self.table.unfreeze()
        self._set_step(AppStep.INDEX, INDEX_PROMPT, buffer, status=status)
        self.data = AppData()

    def start_save(self, buffer: Buffer, save_as_zip: bool | None = None) -> None:
        """Start saving generated parameter files."""
        if not (product_info := self.session.product_info):
            return self._abort("No connection or product info yet.")

        if not self.table.descriptions:
            return self._abort("Nothing to save: map at least one parameter first.")

        if save_as_zip is None and not self.zip_output:
            return self._set_step(AppStep.ZIP, ZIP_PROMPT, buffer)

        self.data.save_as_zip = self.zip_output if save_as_zip is None else save_as_zip
        slug = model_slug(product_info.model)
        target_path = (
            zip_archive_path(self.output_dir, slug)
            if self.data.save_as_zip
            else custom_module_path(self.output_dir, slug)
        )
        if target_path.is_file():
            prompt = f"Overwrite existing {target_path.name}? [y/N]: "
            return self._set_step(AppStep.OVERWRITE, prompt, buffer)

        _save_files(self)
        self.reset_app(buffer, status=self.status)

    def dispatch_enter(self, buffer: Buffer) -> None:
        """Dispatch enter key press to current step handler."""
        handler: Callable[[str, Buffer], None] = getattr(self, f"step_{self.step}")
        handler(buffer.text.strip(), buffer)

    def step_index(self, text: str, buffer: Buffer) -> None:
        """Handle index step."""
        if text.isdigit() and (row := self.table.get(index := int(text))):
            self.table.clear_changed(index)
            self.table.freeze()
            self.data.index = index
            self._set_step(AppStep.NAME, NAME_PROMPT, buffer, text=row.name)
            return

        self._set_step(
            AppStep.INDEX, INDEX_PROMPT, buffer, status="Index must exist in table."
        )

    def step_name(self, text: str, buffer: Buffer) -> None:
        """Handle name step."""
        index = cast(int, self.data.index)
        if not text:
            return self._delete_or_cancel(index, buffer)

        if not NAME_REGEX.match(text):
            return self._abort(
                "Name must start with a lowercase letter and contain only "
                "lowercase letters, numbers, and underscores."
            )

        for other_index, description in self.table.descriptions.items():
            if other_index != index and description.name == text:
                return self._abort(
                    f"Name '{text}' is already used by index {other_index}."
                )

        self.data.name = text
        row = cast(Row, self.table.get(index))
        self.data.apply_template(
            self._get_template_description(self.data.name, row.description),
            parameter_type=(
                _ParameterType.SWITCH
                if row.values.min_value == 0 and row.values.max_value == 1
                else _ParameterType.NUMBER
            ),
        )
        self._set_step(
            AppStep.TYPE,
            f"Parameter type ({AVAILABLE_TYPES}) [{self.data.default_type}]: ",
            buffer,
        )

    def step_type(self, text: str, buffer: Buffer) -> None:
        """Handle type step."""
        try:
            choice = _ParameterType(text.lower() or self.data.default_type)
        except ValueError:
            return self._abort(f"Type must be one of the following: {AVAILABLE_TYPES}.")

        match choice:
            case _ParameterType.SWITCH:
                self._setup_comment(
                    EcomaxSwitchDescription(name=self.data.name), buffer
                )
            case _ParameterType.NUMBER:
                self._set_step(AppStep.OFFSET, f"Offset [{self.data.offset}]: ", buffer)

    def step_offset(self, text: str, buffer: Buffer) -> None:
        """Handle offset step."""
        try:
            self.data.offset = int(text) if text else self.data.offset
            self._set_step(AppStep.STEP, f"Step [{self.data.step}]: ", buffer)
        except ValueError:
            self._abort("Offset must be an integer.")

    def step_step(self, text: str, buffer: Buffer) -> None:
        """Handle step step."""
        try:
            self.data.step = _parse_step(text, default=self.data.step)
            self._set_step(
                AppStep.UNIT,
                f"Unit [{self.data.unit or 'none'}]: ",
                buffer,
                status=f"Available units: {AVAILABLE_UNITS}",
            )
        except ValueError:
            self._abort("Step must be a positive number.")

    def step_unit(self, text: str, buffer: Buffer) -> None:
        """Handle unit step."""
        if not text:
            unit = self.data.unit
        else:
            try:
                unit = UNIT_ALIASES[text.lower()]
            except KeyError:
                return self._abort(
                    f"Unknown unit of measurement. Available: {AVAILABLE_UNITS}"
                )

        description = EcomaxNumberDescription(
            name=self.data.name,
            step=self.data.step,
            offset=self.data.offset,
            unit_of_measurement=unit,
        )
        self._setup_comment(description, buffer)

    def step_comment(self, text: str, buffer: Buffer) -> None:
        """Handle comment step."""
        self.data.comment = text.lstrip("#").strip()
        self._setup_confirm(buffer)

    def step_confirm(self, text: str, buffer: Buffer) -> None:
        """Handle confirm step."""
        if _is_yes(text):
            index = cast(int, self.data.index)
            description = cast(EcomaxParameterDescription, self.data.description)
            self.table.set_description(index, description, comment=self.data.comment)
            status = f"Stored parameter {index}."
        else:
            status = "Discarded."

        self.reset_app(buffer, status=status)

    def step_zip(self, text: str, buffer: Buffer) -> None:
        """Handle ZIP archive confirmation step."""
        self.start_save(buffer, save_as_zip=_is_yes(text))

    def step_overwrite(self, text: str, buffer: Buffer) -> None:
        """Handle overwrite step."""
        if _is_yes(text):
            _save_files(self)
            status = self.status
        else:
            status = "Save cancelled."

        self.reset_app(buffer, status=status)

    def _set_step(
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
        buffer.cursor_position = len(text)
        self.status = status

    def _get_template_description(
        self, name: str, description: EcomaxParameterDescription | None
    ) -> EcomaxParameterDescription | None:
        """Return template description from active row or standard parameters."""
        if description and description.name == name:
            return description

        if product_info := self.session.product_info:
            for parameter in PARAMETER_TYPES.get(product_info.type, []):
                if parameter.name == name:
                    return parameter

        return None

    def _delete_or_cancel(self, index: int, buffer: Buffer) -> None:
        """Delete mapped parameter or cancel addition when name is empty."""
        if index in self.table.descriptions:
            self.table.remove_description(index)
            status = f"Deleted parameter {index}."
        else:
            status = "Cancelled."

        self.reset_app(buffer, status=status)

    def _setup_comment(
        self, description: EcomaxParameterDescription, buffer: Buffer
    ) -> None:
        """Set up comment prompt."""
        index = cast(int, self.data.index)
        comment = self.table.comments.get(index, "")
        self.data.description = description
        self._set_step(AppStep.COMMENT, COMMENT_PROMPT, buffer, text=comment)

    def _setup_confirm(self, buffer: Buffer) -> None:
        """Set up confirm prompt."""
        index = cast(int, self.data.index)
        row = cast(Row, self.table.get(index))
        description = cast(EcomaxParameterDescription, self.data.description)
        preview = Row(row.index, row.values, description=description)
        prompt = (
            f"{self.data.name}: {_format_preview_value(preview)}. "
            "Does this match your device? [y/N]: "
        )
        self._set_step(AppStep.CONFIRM, prompt, buffer)

    def _abort(self, message: str) -> None:
        """Abort current step and set status message."""
        self.status = message

    @property
    def max_scroll_offset(self) -> int:
        """Return maximum scroll offset."""
        return max(0, len(self.table) - PAGE_SIZE)


__all__ = (
    "AppData",
    "AppState",
    "AppStep",
)
