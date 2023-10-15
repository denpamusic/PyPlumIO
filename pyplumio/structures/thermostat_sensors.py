"""Contains a thermostat sensors structure decoder."""
from __future__ import annotations

import math
from typing import Final, Generator

from pyplumio import util
from pyplumio.const import (
    ATTR_CURRENT_TEMP,
    ATTR_SCHEDULE,
    ATTR_STATE,
    ATTR_TARGET_TEMP,
    BYTE_UNDEFINED,
)
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_THERMOSTAT_SENSORS: Final = "thermostat_sensors"
ATTR_THERMOSTAT_COUNT: Final = "thermostat_count"
ATTR_CONTACTS: Final = "contacts"

THERMOSTAT_SENSORS_SIZE: Final = 9


class ThermostatSensorsStructure(StructureDecoder):
    """Represents a thermostats sensors data structure."""

    _offset: int = 0
    _contact_mask: int = 1
    _schedule_mask: int = 1 << 3

    def _unpack_thermostat_sensors(
        self, message: bytearray, contacts: int
    ) -> EventDataType | None:
        """Unpack sensors for a thermostat."""
        current_temp = util.unpack_float(message[self._offset + 1 : self._offset + 5])[
            0
        ]
        target_temp = util.unpack_float(
            message[self._offset + 5 : self._offset + THERMOSTAT_SENSORS_SIZE]
        )[0]

        try:
            if not math.isnan(current_temp) and target_temp > 0:
                return {
                    ATTR_STATE: message[self._offset],
                    ATTR_CURRENT_TEMP: current_temp,
                    ATTR_TARGET_TEMP: target_temp,
                    ATTR_CONTACTS: bool(contacts & self._contact_mask),
                    ATTR_SCHEDULE: bool(contacts & self._schedule_mask),
                }

            return None
        finally:
            self._contact_mask <<= 1
            self._schedule_mask <<= 1
            self._offset += THERMOSTAT_SENSORS_SIZE

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
            return ensure_device_data(data), offset + 1

        contacts = message[offset]
        thermostats = message[offset + 1]
        self._offset = offset + 2
        return (
            ensure_device_data(
                data,
                {
                    ATTR_THERMOSTAT_SENSORS: dict(
                        self._thermostat_sensors(message, thermostats, contacts)
                    ),
                    ATTR_THERMOSTAT_COUNT: thermostats,
                },
            ),
            self._offset,
        )
