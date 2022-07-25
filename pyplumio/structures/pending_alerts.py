"""Contains alarms structure decoder."""
from __future__ import annotations

from typing import Optional, Tuple

from pyplumio.const import ATTR_PENDING_ALERTS
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import Structure


class PendingAlertsStructure(Structure):
    """Represents current alert data structure."""

    def encode(self, data: DeviceDataType) -> bytearray:
        """Encode device data to bytearray message."""
        return bytearray()

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        if data is None:
            data = {}

        alerts_number = message[offset]
        data[ATTR_PENDING_ALERTS] = [message[offset + i] for i in range(alerts_number)]
        return data, (offset + alerts_number + 1)
