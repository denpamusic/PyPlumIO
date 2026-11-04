"""Contains the parameter table model for the PyPlumIO CLI."""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
import importlib.util
from pathlib import Path
from typing import Final

from pyplumio.const import STATE_OFF, STATE_ON, State
from pyplumio.parameters import Numeric, ParameterDescription, ParameterValues
from pyplumio.parameters.custom import ParameterOverride, custom_class_name, model_slug
from pyplumio.parameters.ecomax import EcomaxNumberDescription, EcomaxSwitchDescription

CHANGED_ROW_INTERVALS: Final = 5


def unpack_parameter_value(
    raw_value: int, description: ParameterDescription | None
) -> Numeric | State:
    """Unpack parameter value matching library logic."""
    if isinstance(description, EcomaxSwitchDescription):
        return STATE_ON if raw_value == 1 else STATE_OFF
    if isinstance(description, EcomaxNumberDescription):
        val = round(
            (raw_value - description.offset) * description.step, description.precision
        )
        return int(val) if float(description.step).is_integer() else val
    return raw_value


@dataclass(slots=True)
class Row:
    """Represents a row in the parameter table."""

    index: int
    values: ParameterValues
    remaining_updates: int = 0
    description: EcomaxNumberDescription | EcomaxSwitchDescription | None = None

    @property
    def changed(self) -> bool:
        """Return whether row was recently changed."""
        return self.remaining_updates > 0

    @changed.setter
    def changed(self, value: bool) -> None:
        """Set whether row was recently changed."""
        self.remaining_updates = CHANGED_ROW_INTERVALS if value else 0

    def clear_changed(self) -> None:
        """Clear changed state."""
        self.remaining_updates = 0

    @property
    def name(self) -> str:
        """Return parameter name."""
        return self.description.name if self.description else ""

    @property
    def value(self) -> Numeric | State:
        """Return unpacked parameter value."""
        return unpack_parameter_value(self.values.value, self.description)

    @property
    def min_value(self) -> Numeric | State:
        """Return unpacked minimum value."""
        if isinstance(self.description, EcomaxSwitchDescription):
            return STATE_OFF
        return unpack_parameter_value(self.values.min_value, self.description)

    @property
    def max_value(self) -> Numeric | State:
        """Return unpacked maximum value."""
        if isinstance(self.description, EcomaxSwitchDescription):
            return STATE_ON
        return unpack_parameter_value(self.values.max_value, self.description)


class ParameterTable:
    """Represents a table of ecoMAX parameters."""

    __slots__ = ("descriptions", "overrides", "_has_previous", "_rows")

    descriptions: dict[int, ParameterDescription]
    overrides: tuple[ParameterOverride, ...]
    _has_previous: bool
    _rows: dict[int, Row]

    def __init__(
        self,
        descriptions: dict[int, ParameterDescription] | None = None,
        overrides: Sequence[ParameterOverride] | None = None,
    ) -> None:
        """Initialize the parameter table."""
        self.descriptions = dict(descriptions or {})
        self.overrides = tuple(overrides or ())
        self._rows, self._has_previous = {}, False

    def _update_row(self, index: int, values: ParameterValues) -> bool:
        """Update existing row or create a new one, returning True if changed."""
        if row := self._rows.get(index):
            changed = self._has_previous and (row.values != values)
            if changed:
                row.remaining_updates = CHANGED_ROW_INTERVALS
            row.values = values
            return changed

        desc = self.descriptions.get(index)
        typed_desc = (
            desc
            if isinstance(desc, (EcomaxNumberDescription, EcomaxSwitchDescription))
            else None
        )
        self._rows[index] = Row(index, values, description=typed_desc)
        return False

    def _decrement_intervals(self, changed_indices: set[int]) -> None:
        """Decrement remaining intervals for unchanged rows."""
        if not self._has_previous:
            return
        for index, row in self._rows.items():
            if index not in changed_indices and row.remaining_updates > 0:
                row.remaining_updates -= 1

    def update(self, parameters: Sequence[tuple[int, ParameterValues]]) -> None:
        """Update table rows from decoded parameters."""
        changed_indices = {
            index for index, values in parameters if self._update_row(index, values)
        }
        self._decrement_intervals(changed_indices)
        self._has_previous = True

    def rows(self) -> list[Row]:
        """Return sorted rows."""
        return sorted(self._rows.values(), key=lambda row: row.index)

    def get(self, index: int) -> Row | None:
        """Get row by index."""
        return self._rows.get(index)

    def clear_changed(self, index: int) -> None:
        """Clear changed state for a parameter index."""
        if row := self._rows.get(index):
            row.clear_changed()

    def set_description(
        self,
        index: int,
        description: EcomaxNumberDescription | EcomaxSwitchDescription | None,
    ) -> None:
        """Set or remove description for a parameter index."""
        if description is not None:
            self.descriptions[index] = description
        else:
            self.descriptions.pop(index, None)
        if row := self._rows.get(index):
            row.description = description


def load_custom_parameters(
    model: str, output_dir: Path
) -> tuple[dict[int, ParameterDescription], tuple[ParameterOverride, ...]]:
    """Load existing custom parameters for a model."""
    slug, class_name = model_slug(model), custom_class_name(model_slug(model))
    module_file = output_dir / "pyplumio" / "parameters" / "custom" / f"{slug}.py"
    custom_class: type | None = None
    if module_file.is_file() and (
        spec := importlib.util.spec_from_file_location(f"_custom_{slug}", module_file)
    ):
        if spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            custom_class = getattr(module, class_name, None)

    if custom_class is None:
        with suppress(ImportError, AttributeError):
            custom_class = getattr(
                importlib.import_module(f"pyplumio.parameters.custom.{slug}"),
                class_name,
                None,
            )

    if custom_class is None:
        return {}, ()
    return dict(getattr(custom_class, "descriptions", {})), tuple(
        getattr(custom_class, "overrides", ())
    )


__all__ = (
    "CHANGED_ROW_INTERVALS",
    "ParameterTable",
    "Row",
    "load_custom_parameters",
    "unpack_parameter_value",
)
