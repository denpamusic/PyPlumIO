"""Contains mixers structure decoder."""
from __future__ import annotations

import math
from typing import Final, List, Optional, Tuple

from pyplumio import util
from pyplumio.const import ATTR_CURRENT_TEMP, ATTR_TARGET_TEMP
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_PUMP: Final = "pump"
ATTR_MIXER_COUNT: Final = "mixer_count"
ATTR_MIXER_SENSORS: Final = "mixer_sensors"


class MixerSensorsStructure(StructureDecoder):
    """Represents mixers data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        mixer_count = message[offset]
        offset += 1
        mixer_sensors: List[Tuple[int, DeviceDataType]] = []
        for index in range(mixer_count):
            current_temp = util.unpack_float(message[offset : offset + 4])[0]
            if not math.isnan(current_temp):
                sensors: DeviceDataType = {}
                sensors[ATTR_CURRENT_TEMP] = current_temp
                sensors[ATTR_TARGET_TEMP] = message[offset + 4]
                outputs = message[offset + 6]
                sensors[ATTR_PUMP] = bool(outputs & 0x01)
                mixer_sensors.append((index, sensors))

            offset += 8

        if not mixer_sensors:
            # No mixer sensors detected.
            return ensure_device_data(data), offset

        return (
            ensure_device_data(
                data,
                {
                    ATTR_MIXER_SENSORS: mixer_sensors,
                    ATTR_MIXER_COUNT: mixer_count,
                },
            ),
            offset,
        )
