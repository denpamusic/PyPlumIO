"""Contains various utility methods."""
from __future__ import annotations


def to_camelcase(text: str, overrides: dict[str, str] = None) -> str:
    """Convert snake_case to CamelCase."""
    if overrides is None:
        return "".join((x.capitalize() or "_") for x in text.split("_"))

    return "".join(
        (x.capitalize() or "_") if x.lower() not in overrides else overrides[x.lower()]
        for x in text.split("_")
    )


def ensure_dict(data: dict | None, *args) -> dict:
    """Create or merge multiple dictionaries."""
    data = data if data is not None else {}
    for new_data in args:
        data |= new_data

    return data
