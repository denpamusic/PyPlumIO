"""Contains a mixer sensors structure decoder."""
from __future__ import annotations

import math
from typing import Final, Generator

from pyplumio.const import ATTR_CURRENT_TEMP, ATTR_TARGET_TEMP
from pyplumio.helpers.data_types import unpack_float
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_PUMP: Final = "pump"
ATTR_MIXER_COUNT: Final = "mixer_count"
ATTR_MIXER_SENSORS: Final = "mixer_sensors"

MIXER_SENSOR_SIZE: Final = 8


class MixerSensorsStructure(StructureDecoder):
    """Represents a mixer sensors data structure."""

    _offset: int

    def _unpack_mixer_sensors(self, message: bytearray) -> EventDataType | None:
        """Unpack sensors for a mixer."""
        current_temp = unpack_float(message[self._offset : self._offset + 4])[0]
        try:
            if not math.isnan(current_temp):
                return {
                    ATTR_CURRENT_TEMP: current_temp,
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
        return (
            ensure_device_data(
                data,
                {
                    ATTR_MIXER_SENSORS: dict(self._mixer_sensors(message, mixers)),
                    ATTR_MIXER_COUNT: mixers,
                },
            ),
            self._offset,
        )
