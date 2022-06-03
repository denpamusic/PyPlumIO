"""Contains product info representation."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ProductInfo:
    """Represents product info provided by UID response."""

    type: int = 0
    product: int = 0
    uid: Optional[str] = None
    logo: int = 0
    image: int = 0
    model: Optional[str] = None


@dataclass
class ConnectedModules:
    """Represents firmware version info."""

    module_a: Optional[str] = None
    module_b: Optional[str] = None
    module_c: Optional[str] = None
    module_lambda: Optional[str] = None
    module_ecoster: Optional[str] = None
    module_panel: Optional[str] = None
