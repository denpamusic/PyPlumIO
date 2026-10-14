"""Contains structure decoders."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pyplumio.frames import Frame


class Structure(ABC):
    """Represents a data structure."""

    __slots__ = ("frame", "_offset")

    frame: Frame
    _offset: int

    def __init__(self, frame: Frame) -> None:
        """Initialize a new structure."""
        self.frame = frame
        self._offset = 0

    @property
    def offset(self) -> int:
        """Return a structure read offset."""
        return self._offset

    @abstractmethod
    def encode(self, data: dict[str, Any]) -> bytearray:
        """Encode message from data."""

    @abstractmethod
    def decode(self, message: bytearray, data: dict[str, Any], offset: int = 0) -> None:
        """Decode message into data."""


class StructureDecoder(Structure, ABC):
    """Represents a structure that only handles decoding."""

    __slots__ = ()

    def encode(self, data: dict[str, Any]) -> bytearray:
        """Encode message from data."""
        return bytearray()

    @abstractmethod
    def decode(self, message: bytearray, data: dict[str, Any], offset: int = 0) -> None:
        """Decode message into data."""


__all__ = ["Structure", "StructureDecoder"]
