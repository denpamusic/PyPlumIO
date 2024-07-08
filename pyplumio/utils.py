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


K = TypeVar("K")
V = TypeVar("V")


def ensure_dict(initial: dict[K, V] | None, *args: dict[K, V]) -> dict[K, V]:
    """Create or merge multiple dictionaries."""
    data = initial if initial is not None else {}
    for extra in args:
        data |= extra

    return data
