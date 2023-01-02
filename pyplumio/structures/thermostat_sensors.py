"""Contains thermostats structure decoder."""
from __future__ import annotations

import math
from typing import Final, List, Optional, Tuple

from pyplumio import util
from pyplumio.const import (
    ATTR_CURRENT_TEMP,
    ATTR_SCHEDULE,
    ATTR_STATE,
    ATTR_TARGET_TEMP,
    BYTE_UNDEFINED,
)
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_THERMOSTAT_SENSORS: Final = "thermostat_sensors"
ATTR_THERMOSTAT_COUNT: Final = "thermostat_count"
ATTR_CONTACTS: Final = "contacts"


class ThermostatSensorsStructure(StructureDecoder):
    """Represents thermostats data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        if message[offset] == BYTE_UNDEFINED:
            return ensure_device_data(data), offset + 1

        contacts = message[offset]
        thermostat_count = message[offset + 1]
        offset += 2
        contact_mask = 1
        schedule_mask = 1 << 3
        thermostat_sensors: List[Tuple[int, DeviceDataType]] = []
        for index in range(thermostat_count):
            current_temp = util.unpack_float(message[offset + 1 : offset + 5])[0]
            if not math.isnan(current_temp):
                sensors: DeviceDataType = {}
                sensors[ATTR_STATE] = message[offset]
                sensors[ATTR_CURRENT_TEMP] = current_temp
                sensors[ATTR_TARGET_TEMP] = util.unpack_float(
                    message[offset + 5 : offset + 9]
                )[0]
                sensors[ATTR_CONTACTS] = bool(contacts & contact_mask)
                sensors[ATTR_SCHEDULE] = bool(contacts & schedule_mask)
                thermostat_sensors.append((index, sensors))

            contact_mask = contact_mask << 1
            schedule_mask = schedule_mask << 1
            offset += 9

        return (
            ensure_device_data(
                data,
                {
                    ATTR_THERMOSTAT_SENSORS: thermostat_sensors,
                    ATTR_THERMOSTAT_COUNT: thermostat_count,
                },
            ),
            offset,
        )
