"""Contains thermostats structure decoder."""
from __future__ import annotations

from typing import Final, List, Optional, Tuple

from pyplumio import util
from pyplumio.const import ATTR_THERMOSTATS, BYTE_UNDEFINED
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_ECOSTER_CONTACTS: Final = "contacts"
ATTR_ECOSTER_SCHEDULE: Final = "schedule"
ATTR_ECOSTER_STATE: Final = "state"
ATTR_ECOSTER_TEMP: Final = "temp"
ATTR_ECOSTER_TARGET: Final = "target"


class ThermostatsStructure(StructureDecoder):
    """Represents thermostats data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        if message[offset] == BYTE_UNDEFINED:
            return ensure_device_data(data), offset + 1

        therm_contacts = message[offset]
        offset += 1
        therm_number = message[offset]
        offset += 1
        thermostats: List[DeviceDataType] = []
        contact_mask = 1
        schedule_mask = 1 << 3
        for _ in range(therm_number):
            therm: DeviceDataType = {}
            therm[ATTR_ECOSTER_CONTACTS] = bool(therm_contacts & contact_mask)
            therm[ATTR_ECOSTER_SCHEDULE] = bool(therm_contacts & schedule_mask)
            therm[ATTR_ECOSTER_STATE] = message[offset]
            therm[ATTR_ECOSTER_TEMP] = util.unpack_float(
                message[offset + 1 : offset + 5]
            )[0]
            therm[ATTR_ECOSTER_TARGET] = util.unpack_float(
                message[offset + 5 : offset + 9]
            )[0]
            thermostats.append(therm)
            offset += 9
            contact_mask = contact_mask << 1
            schedule_mask = schedule_mask << 1

        return ensure_device_data(data, {ATTR_THERMOSTATS: thermostats}), offset
