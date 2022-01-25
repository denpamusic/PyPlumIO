"""Contains singleton pattern implementation."""
from __future__ import annotations


class Singleton:
    """Singleton pattern implementation."""

    def __new__(cls: str) -> Singleton:
        """Gets singleton instance.

        Keyword arguments:
        cls - current class name
        """
        if not hasattr(cls, "instance"):
            cls.instance = super(Singleton, cls).__new__(cls)

        return cls.instance
