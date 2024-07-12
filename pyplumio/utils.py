"""Contains various utility methods."""

from __future__ import annotations

from typing import TypeVar


def to_camelcase(text: str, overrides: dict[str, str] | None = None) -> str:
    """Convert snake_case to CamelCase."""
    if overrides is None:
        return "".join((x.capitalize() or "_") for x in text.split("_"))

    return "".join(
        (x.capitalize() or "_") if x.lower() not in overrides else overrides[x.lower()]
        for x in text.split("_")
    )


KT = TypeVar("KT")  # Key type.
VT = TypeVar("VT")  # Value type.


def ensure_dict(initial: dict[KT, VT] | None, *args: dict[KT, VT]) -> dict[KT, VT]:
    """Create or merge multiple dictionaries."""
    data = initial if initial is not None else {}
    for extra in args:
        data |= extra

    return data
