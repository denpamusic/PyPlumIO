"""Contains thermostats structure decoder."""
from __future__ import annotations

from typing import Final, List, Optional, Tuple

from pyplumio import util
from pyplumio.const import ATTR_THERMOSTATS
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import Structure

ECOSTER_CONTACTS: Final = "contacts"
ECOSTER_SCHEDULE: Final = "schedule"
ECOSTER_MODE: Final = "mode"
ECOSTER_TEMP: Final = "temp"
ECOSTER_TARGET: Final = "target"


class ThermostatsStructure(Structure):
    """Represents thermostats data structure."""

    def encode(self, data: DeviceDataType) -> bytearray:
        return bytearray()

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        if data is None:
            data = {}

        if message[offset] == 0xFF:
            offset += 1
            return data, offset

        therm_contacts = message[offset]
        offset += 1
        therm_number = message[offset]
        offset += 1
        thermostats: List[DeviceDataType] = []
        contact_mask = 1
        schedule_mask = 1 << 3
        for _ in range(therm_number):
            therm: DeviceDataType = {}
            therm[ECOSTER_CONTACTS] = bool(therm_contacts & contact_mask)
            therm[ECOSTER_SCHEDULE] = bool(therm_contacts & schedule_mask)
            therm[ECOSTER_MODE] = message[offset]
            therm[ECOSTER_TEMP] = util.unpack_float(message[offset + 1 : offset + 5])[0]
            therm[ECOSTER_TARGET] = util.unpack_float(message[offset + 5 : offset + 9])[
                0
            ]
            thermostats.append(therm)
            offset += 9
            contact_mask = contact_mask << 1
            schedule_mask = schedule_mask << 1

        data[ATTR_THERMOSTATS] = thermostats

        return data, offset
