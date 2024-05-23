"""Contains various utility methods."""

from __future__ import annotations

from functools import cache
from typing import Any


@cache
def to_camelcase(text: str, overrides: frozenset[tuple[str, str]] | None = None) -> str:
    """Convert snake_case to CamelCase."""
    if overrides is None:
        return "".join((x.capitalize() or "_") for x in text.split("_"))

    overrides_dict = dict(overrides)
    return "".join(
        (x.capitalize() or "_")
        if x.lower() not in overrides_dict
        else overrides_dict[x.lower()]
        for x in text.split("_")
    )


def ensure_dict(data: dict | None, *args: Any) -> dict:
    """Create or merge multiple dictionaries."""
    data = data if data is not None else {}
    for new_data in args:
        data |= new_data

    return data
