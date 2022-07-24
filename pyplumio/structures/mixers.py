"""Contains mixers structure decoder."""
from __future__ import annotations

from typing import Final, List, Optional, Tuple

from pyplumio import util
from pyplumio.const import ATTR_MIXER_SENSORS
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import Structure

MIXER_TEMP: Final = "temp"
MIXER_TARGET_TEMP: Final = "target_temp"
MIXER_PUMP_OUTPUT: Final = "mixer_pump"
MIXER_DATA: Tuple[str, ...] = (
    MIXER_TEMP,
    MIXER_TARGET_TEMP,
    MIXER_PUMP_OUTPUT,
)


class MixersStructure(Structure):
    """Represents mixers data structure."""

    def encode(self, data: DeviceDataType) -> bytearray:
        """Encode device data to bytearray message."""
        return bytearray()

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        if data is None:
            data = {}

        mixers_number = message[offset]
        offset += 1
        mixers: List[DeviceDataType] = []
        for _ in range(mixers_number):
            mixer: DeviceDataType = {}
            mixer[MIXER_TEMP] = util.unpack_float(message[offset : offset + 4])[0]
            mixer[MIXER_TARGET_TEMP] = message[offset + 4]
            mixer_outputs = message[offset + 6]
            mixer[MIXER_PUMP_OUTPUT] = bool(mixer_outputs & 0x01)
            mixers.append(mixer)
            offset += 8

        data[ATTR_MIXER_SENSORS] = mixers

        return data, offset
