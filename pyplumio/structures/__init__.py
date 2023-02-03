"""Contains structure decoders."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from pyplumio.frames import Frame
from pyplumio.helpers.typing import DeviceDataType


def ensure_device_data(data: DeviceDataType | None, *args) -> DeviceDataType:
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
    def encode(self, data: DeviceDataType) -> bytearray:
        """Encode device data to bytearray message."""

    @abstractmethod
    def decode(
        self,
        message: bytearray,
        offset: int = 0,
        data: DeviceDataType | None = None,
    ) -> tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""


class StructureDecoder(Structure, ABC):
    """Represent structure that only handles decoding."""

    def encode(self, data: DeviceDataType) -> bytearray:
        """Encode device data to bytearray message."""
        return bytearray()

    @abstractmethod
    def decode(
        self, message: bytearray, offset: int = 0, data: DeviceDataType | None = None
    ) -> tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
