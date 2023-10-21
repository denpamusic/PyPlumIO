"""Contains a statuses structure decoder."""
from __future__ import annotations

from typing import Final

from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_HEATING_TARGET: Final = "heating_target"
ATTR_HEATING_STATUS: Final = "heating_status"
ATTR_WATER_HEATER_TARGET: Final = "water_heater_target"
ATTR_WATER_HEATER_STATUS: Final = "water_heater_status"

STATUSES: tuple[str, ...] = (
    ATTR_HEATING_TARGET,
    ATTR_HEATING_STATUS,
    ATTR_WATER_HEATER_TARGET,
    ATTR_WATER_HEATER_STATUS,
)

STATUSES_SIZE: Final = 4


class StatusesStructure(StructureDecoder):
    """Represents a statuses data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        return (
            ensure_dict(
                data,
                {
                    status: message[offset + index]
                    for index, status in enumerate(STATUSES)
                },
            ),
            offset + STATUSES_SIZE,
        )
