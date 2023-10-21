"""Contains structure decoders."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from pyplumio.frames import Frame
from pyplumio.helpers.typing import EventDataType


@dataclass
class StructureDataClass:
    "Represents a structure dataclass mixin."

    frame: Frame


class Structure(ABC, StructureDataClass):
    """Represents a data structure."""

    @abstractmethod
    def encode(self, data: EventDataType) -> bytearray:
        """Encode data to the bytearray message."""

    @abstractmethod
    def decode(
        self,
        message: bytearray,
        offset: int = 0,
        data: EventDataType | None = None,
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""


class StructureDecoder(Structure, ABC):
    """Represents a structure that only handles decoding."""

    def encode(self, data: EventDataType) -> bytearray:
        """Encode data to the bytearray message."""
        return bytearray()

    @abstractmethod
    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
