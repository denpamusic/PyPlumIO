"""Contains the parameter table model for the PyPlumIO CLI."""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
import importlib.util
import logging
from pathlib import Path
from typing import Final

from pyplumio.const import STATE_OFF, STATE_ON, State
from pyplumio.parameters import Numeric, ParameterDescription, ParameterValues
from pyplumio.parameters.custom import ParameterOverride, custom_class_name, model_slug
from pyplumio.parameters.ecomax import EcomaxNumberDescription, EcomaxSwitchDescription

_LOGGER = logging.getLogger(__name__)

CHANGED_ROW_INTERVALS: Final = 5


def unpack_parameter_value(
    raw_value: int, description: ParameterDescription | None
) -> Numeric | State:
    """Unpack parameter value matching library logic."""
    if isinstance(description, EcomaxSwitchDescription):
        return STATE_ON if raw_value == 1 else STATE_OFF
    if isinstance(description, EcomaxNumberDescription):
        unpacked_value = round(
            (raw_value - description.offset) * description.step, description.precision
        )
        return (
            int(unpacked_value)
            if float(description.step).is_integer()
            else unpacked_value
        )
    return raw_value


@dataclass(slots=True)
class Row:
    """Represents a row in the parameter table."""

    index: int
    values: ParameterValues
    remaining_updates: int = 0
    description: EcomaxNumberDescription | EcomaxSwitchDescription | None = None
    change_order: int = 0

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

    __slots__ = (
        "descriptions",
        "overrides",
        "_change_counter",
        "_frozen_order",
        "_has_previous",
        "_rows",
    )

    descriptions: dict[int, ParameterDescription]
    overrides: tuple[ParameterOverride, ...]
    _change_counter: int
    _frozen_order: list[int] | None
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
        self._rows, self._has_previous, self._change_counter = {}, False, 0
        self._frozen_order = None

    def freeze(self) -> None:
        """Freeze row display order."""
        self._frozen_order = [row.index for row in self.rows()]

    def unfreeze(self) -> None:
        """Unfreeze row display order."""
        self._frozen_order = None

    @property
    def is_frozen(self) -> bool:
        """Return whether row order is frozen."""
        return self._frozen_order is not None

    def _update_row(self, index: int, values: ParameterValues) -> bool:
        """Update existing row or create a new one, returning True if changed."""
        if row := self._rows.get(index):
            changed = self._has_previous and (row.values != values)
            if changed:
                row.remaining_updates = CHANGED_ROW_INTERVALS
            row.values = values
            return changed

        description = self.descriptions.get(index)
        typed_description = (
            description
            if isinstance(
                description, (EcomaxNumberDescription, EcomaxSwitchDescription)
            )
            else None
        )
        self._rows[index] = Row(index, values, description=typed_description)
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
        if changed_indices:
            self._change_counter += 1
            for index in changed_indices:
                self._rows[index].change_order = self._change_counter
        self._decrement_intervals(changed_indices)
        self._has_previous = True

    def __len__(self) -> int:
        """Return number of rows in the table."""
        return len(self._rows)

    def rows(self) -> list[Row]:
        """Return sorted rows, with changed rows stacked at the top."""
        if self._frozen_order is not None:
            seen_indices = set(self._frozen_order)
            frozen_rows = [
                self._rows[index] for index in self._frozen_order if index in self._rows
            ]
            extra_rows = [
                row for row in self._rows.values() if row.index not in seen_indices
            ]
            return frozen_rows + sorted(
                extra_rows, key=lambda row: (-row.change_order, row.index)
            )
        return sorted(
            self._rows.values(), key=lambda row: (-row.change_order, row.index)
        )

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
            try:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                custom_class = getattr(module, class_name, None)
            except Exception as err:
                _LOGGER.warning(
                    "Failed to load custom parameters from %s: %s", module_file, err
                )

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
