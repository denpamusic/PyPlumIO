"""Contains alarms structure decoder."""
from __future__ import annotations

from typing import Optional, Tuple

from pyplumio.const import ATTR_PENDING_ALERTS
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, make_device_data


class PendingAlertsStructure(StructureDecoder):
    """Represents current alert data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        alerts_number = message[offset]
        pending_alerts = [message[offset + i] for i in range(alerts_number)]
        return make_device_data(data, {ATTR_PENDING_ALERTS: pending_alerts}), (
            offset + alerts_number + 1
        )
