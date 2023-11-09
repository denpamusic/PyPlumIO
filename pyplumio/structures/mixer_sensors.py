"""Contains a mixer sensors structure decoder."""
from __future__ import annotations

import math
from typing import Final, Generator

from pyplumio.const import ATTR_CURRENT_TEMP, ATTR_TARGET_TEMP
from pyplumio.helpers.data_types import Float
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_PUMP: Final = "pump"
ATTR_MIXERS_AVAILABLE: Final = "mixers_available"
ATTR_MIXERS_CONNECTED: Final = "mixers_connected"
ATTR_MIXER_SENSORS: Final = "mixer_sensors"

MIXER_SENSOR_SIZE: Final = 8


class MixerSensorsStructure(StructureDecoder):
    """Represents a mixer sensors data structure."""

    _offset: int

    def _unpack_mixer_sensors(self, message: bytearray) -> EventDataType | None:
        """Unpack sensors for a mixer."""
        current_temp = Float.from_bytes(message, self._offset)
        try:
            if not math.isnan(current_temp.value):
                return {
                    ATTR_CURRENT_TEMP: current_temp.value,
                    ATTR_TARGET_TEMP: message[self._offset + 4],
                    ATTR_PUMP: bool(message[self._offset + 6] & 0x01),
                }

            return None
        finally:
            self._offset += MIXER_SENSOR_SIZE

    def _mixer_sensors(
        self, message: bytearray, mixers: int
    ) -> Generator[tuple[int, EventDataType], None, None]:
        """Get sensors for a mixer."""
        for index in range(mixers):
            if sensors := self._unpack_mixer_sensors(message):
                yield (index, sensors)

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        mixers = message[offset]
        self._offset = offset + 1
        mixer_sensors = dict(self._mixer_sensors(message, mixers))
        return (
            ensure_dict(
                data,
                {
                    ATTR_MIXER_SENSORS: mixer_sensors,
                    ATTR_MIXERS_AVAILABLE: mixers,
                    ATTR_MIXERS_CONNECTED: len(mixer_sensors),
                },
            ),
            self._offset,
        )
