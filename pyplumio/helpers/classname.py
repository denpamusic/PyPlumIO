"""Contains classname helper."""
from __future__ import annotations


class ClassName:
    """Contains helper method to get class name."""

    @classmethod
    def get_classname(cls):
        """Return class name."""
        return cls.__name__
