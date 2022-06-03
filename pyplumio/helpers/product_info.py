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
