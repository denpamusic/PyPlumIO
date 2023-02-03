"""Contains product info dataclasses."""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, unique


@unique
class ProductType(IntEnum):
    """Contains product types."""

    ECOMAX_P = 0
    ECOMAX_I = 1


@dataclass
class ProductInfo:
    """Represents product info provided by UID response."""

    type: int
    product: int
    uid: str
    logo: int
    image: int
    model: str


@dataclass
class ConnectedModules:
    """Represents firmware version info."""

    module_a: str | None = None
    module_b: str | None = None
    module_c: str | None = None
    module_lambda: str | None = None
    module_ecoster: str | None = None
    module_panel: str | None = None
