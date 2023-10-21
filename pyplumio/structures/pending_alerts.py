"""Contains a pending alerts structure decoder."""
from __future__ import annotations

from typing import Final

from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_PENDING_ALERTS: Final = "pending_alerts"


class PendingAlertsStructure(StructureDecoder):
    """Represents a pending alerts structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        alerts_number = message[offset]
        return ensure_dict(data, {ATTR_PENDING_ALERTS: alerts_number}), (
            offset + alerts_number + 1
        )
