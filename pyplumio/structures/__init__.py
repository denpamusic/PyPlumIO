"""Contains structure decoders."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from pyplumio.frames import Frame
from pyplumio.helpers.typing import EventDataType


def ensure_device_data(data: EventDataType | None, *args) -> EventDataType:
    """Make new or merge multiple device data."""
    if data is None:
        data = {}

    for new_data in args:
        data |= new_data

    return data


@dataclass
class StructureDataClass:
    "Represents structure dataclass mixin."

    frame: Frame


class Structure(ABC, StructureDataClass):
    """Represents data structure."""

    @abstractmethod
    def encode(self, data: EventDataType) -> bytearray:
        """Encode device data to bytearray message."""

    @abstractmethod
    def decode(
        self,
        message: bytearray,
        offset: int = 0,
        data: EventDataType | None = None,
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""


class StructureDecoder(Structure, ABC):
    """Represent structure that only handles decoding."""

    def encode(self, data: EventDataType) -> bytearray:
        """Encode device data to bytearray message."""
        return bytearray()

    @abstractmethod
    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
