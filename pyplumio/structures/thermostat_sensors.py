"""Contains thermostats structure decoder."""
from __future__ import annotations

import math
from typing import Final, List, Optional, Tuple

from pyplumio import util
from pyplumio.const import (
    ATTR_THERMOSTAT_SENSORS,
    ATTR_THERMOSTATS_NUMBER,
    BYTE_UNDEFINED,
)
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_THERMOSTAT_STATE: Final = "thermostat_state"
ATTR_THERMOSTAT_TEMP: Final = "thermostat_temp"
ATTR_THERMOSTAT_TARGET: Final = "thermostat_target"
ATTR_THERMOSTAT_CONTACTS: Final = "thermostat_contacts"
ATTR_THERMOSTAT_SCHEDULE: Final = "thermostat_schedule"


class ThermostatSensorsStructure(StructureDecoder):
    """Represents thermostats data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        if message[offset] == BYTE_UNDEFINED:
            return ensure_device_data(data), offset + 1

        thermostats_contacts = message[offset]
        offset += 1
        thermostats_number = message[offset]
        offset += 1
        contact_mask = 1
        schedule_mask = 1 << 3
        thermostat_sensors: List[Tuple[int, DeviceDataType]] = []
        for thermostat_number in range(thermostats_number):
            thermostat_temp = util.unpack_float(message[offset + 1 : offset + 5])[0]
            if not math.isnan(thermostat_temp):
                thermostat: DeviceDataType = {}
                thermostat[ATTR_THERMOSTAT_STATE] = message[offset]
                thermostat[ATTR_THERMOSTAT_TEMP] = thermostat_temp
                thermostat[ATTR_THERMOSTAT_TARGET] = util.unpack_float(
                    message[offset + 5 : offset + 9]
                )[0]
                thermostat[ATTR_THERMOSTAT_CONTACTS] = bool(
                    thermostats_contacts & contact_mask
                )
                thermostat[ATTR_THERMOSTAT_SCHEDULE] = bool(
                    thermostats_contacts & schedule_mask
                )
                thermostat_sensors.append((thermostat_number, thermostat))

            contact_mask = contact_mask << 1
            schedule_mask = schedule_mask << 1
            offset += 9

        if not thermostat_sensors:
            # No thermostats sensors detected.
            return data, offset

        return (
            ensure_device_data(
                data,
                {
                    ATTR_THERMOSTAT_SENSORS: thermostat_sensors,
                    ATTR_THERMOSTATS_NUMBER: thermostats_number,
                },
            ),
            offset,
        )
