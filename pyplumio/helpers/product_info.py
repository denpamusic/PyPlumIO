"""Contains product info dataclasses."""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, unique
from typing import Optional


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

    module_a: Optional[str] = None
    module_b: Optional[str] = None
    module_c: Optional[str] = None
    module_lambda: Optional[str] = None
    module_ecoster: Optional[str] = None
    module_panel: Optional[str] = None
