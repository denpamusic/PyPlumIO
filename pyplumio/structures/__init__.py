"""Contains structure decoders."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pyplumio.frames import Frame


class Structure(ABC):
    """Represents a data structure."""

    __slots__ = ("frame",)

    frame: Frame

    def __init__(self, frame: Frame) -> None:
        """Initialize a new structure."""
        self.frame = frame

    @abstractmethod
    def encode(self, data: dict[str, Any]) -> bytearray:
        """Encode data to the bytearray message."""

    @abstractmethod
    def decode(
        self,
        message: bytearray,
        offset: int = 0,
        data: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], int]:
        """Decode bytes and return message data and offset."""


class StructureDecoder(Structure, ABC):
    """Represents a structure that only handles decoding."""

    __slots__ = ()

    def encode(self, data: dict[str, Any]) -> bytearray:
        """Encode data to the bytearray message."""
        return bytearray()

    @abstractmethod
    def decode(
        self, message: bytearray, offset: int = 0, data: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], int]:
        """Decode bytes and return message data and offset."""


__all__ = ["Structure", "StructureDecoder"]
