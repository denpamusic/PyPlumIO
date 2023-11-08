"""Contains a thermostat sensors structure decoder."""
from __future__ import annotations

import math
from typing import Final, Generator

from pyplumio.const import (
    ATTR_CURRENT_TEMP,
    ATTR_SCHEDULE,
    ATTR_STATE,
    ATTR_TARGET_TEMP,
    BYTE_UNDEFINED,
)
from pyplumio.helpers.data_types import Float
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_THERMOSTAT_SENSORS: Final = "thermostat_sensors"
ATTR_THERMOSTATS_AVAILABLE: Final = "thermostats_available"
ATTR_THERMOSTATS_CONNECTED: Final = "thermostats_connected"
ATTR_CONTACTS: Final = "contacts"


class ThermostatSensorsStructure(StructureDecoder):
    """Represents a thermostats sensors data structure."""

    _offset: int
    _contact_mask: int = 1
    _schedule_mask: int = 1 << 3

    def _unpack_thermostat_sensors(
        self, message: bytearray, contacts: int
    ) -> EventDataType | None:
        """Unpack sensors for a thermostat."""
        state = message[self._offset]
        self._offset += 1
        current_temp = Float.from_bytes(message, self._offset)
        self._offset += current_temp.size
        target_temp = Float.from_bytes(message, self._offset)
        self._offset += target_temp.size

        try:
            if not math.isnan(current_temp.value) and target_temp.value > 0:
                return {
                    ATTR_STATE: state,
                    ATTR_CURRENT_TEMP: current_temp.value,
                    ATTR_TARGET_TEMP: target_temp.value,
                    ATTR_CONTACTS: bool(contacts & self._contact_mask),
                    ATTR_SCHEDULE: bool(contacts & self._schedule_mask),
                }

            return None
        finally:
            self._contact_mask <<= 1
            self._schedule_mask <<= 1

    def _thermostat_sensors(
        self, message: bytearray, thermostats: int, contacts: int
    ) -> Generator[tuple[int, EventDataType], None, None]:
        """Get sensors for a thermostat."""
        for index in range(thermostats):
            if sensors := self._unpack_thermostat_sensors(message, contacts):
                yield (index, sensors)

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        if message[offset] == BYTE_UNDEFINED:
            return ensure_dict(data), offset + 1

        contacts = message[offset]
        thermostats = message[offset + 1]
        self._offset = offset + 2
        thermostat_sensors = dict(
            self._thermostat_sensors(message, thermostats, contacts)
        )
        return (
            ensure_dict(
                data,
                {
                    ATTR_THERMOSTAT_SENSORS: thermostat_sensors,
                    ATTR_THERMOSTATS_AVAILABLE: thermostats,
                    ATTR_THERMOSTATS_CONNECTED: len(thermostat_sensors),
                },
            ),
            self._offset,
        )
