"""Contains alarms structure decoder."""
from __future__ import annotations

from typing import Final, Optional, Tuple

from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_PENDING_ALERTS: Final = "pending_alerts"


class PendingAlertsStructure(StructureDecoder):
    """Represents current alert data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        alerts_number = message[offset]
        return ensure_device_data(data, {ATTR_PENDING_ALERTS: alerts_number}), (
            offset + alerts_number + 1
        )
