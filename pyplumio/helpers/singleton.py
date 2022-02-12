"""Contains singleton pattern implementation."""
from __future__ import annotations

from typing import Type


class Singleton:
    """Singleton pattern implementation."""

    def __new__(cls: Type[Singleton]) -> Singleton:
        """Gets singleton instance.

        Keyword arguments:
        cls - current class name
        """
        if not hasattr(cls, "instance"):
            cls.instance = super(Singleton, cls).__new__(cls)

        return cls.instance
