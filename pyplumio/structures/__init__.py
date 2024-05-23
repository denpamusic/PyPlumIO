"""Contains structure decoders."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from pyplumio.frames import Frame


@dataclass
class StructureDataClass:
    """Represents a structure dataclass mixin."""

    __slots__ = ("frame",)

    frame: Frame


class Structure(ABC, StructureDataClass):
    """Represents a data structure."""

    __slots__ = ()

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
