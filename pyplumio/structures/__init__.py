"""Contains structure decoders."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple

from pyplumio.frames import Frame
from pyplumio.helpers.typing import DeviceDataType


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
        data: Optional[DeviceDataType] = None,
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
