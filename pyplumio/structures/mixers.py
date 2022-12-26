"""Contains mixers structure decoder."""
from __future__ import annotations

import math
from typing import Final, List, Optional, Tuple

from pyplumio import util
from pyplumio.const import ATTR_MIXER_SENSORS
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_MIXER_TEMP: Final = "mixer_temp"
ATTR_MIXER_TARGET: Final = "mixer_target"
ATTR_MIXER_PUMP_OUTPUT: Final = "mixer_pump"


class MixersStructure(StructureDecoder):
    """Represents mixers data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        mixers_number = message[offset]
        offset += 1
        mixer_sensors: List[DeviceDataType] = []
        for _ in range(mixers_number):
            mixer_temp = util.unpack_float(message[offset : offset + 4])[0]
            if not math.isnan(mixer_temp):
                mixer: DeviceDataType = {}
                mixer[ATTR_MIXER_TEMP] = mixer_temp
                mixer[ATTR_MIXER_TARGET] = message[offset + 4]
                mixer_outputs = message[offset + 6]
                mixer[ATTR_MIXER_PUMP_OUTPUT] = bool(mixer_outputs & 0x01)
                mixer_sensors.append(mixer)

            offset += 8

        if not mixer_sensors:
            # No mixer sensors detected.
            return data, offset

        return ensure_device_data(data, {ATTR_MIXER_SENSORS: mixer_sensors}), offset
