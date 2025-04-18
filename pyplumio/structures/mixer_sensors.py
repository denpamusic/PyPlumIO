"""Contains a mixer sensors structure decoder."""

from __future__ import annotations

from collections.abc import Generator
import math
from typing import Any, Final

from pyplumio.const import ATTR_CURRENT_TEMP, ATTR_TARGET_TEMP
from pyplumio.helpers.data_types import Float
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_PUMP: Final = "pump"
ATTR_MIXERS_AVAILABLE: Final = "mixers_available"
ATTR_MIXERS_CONNECTED: Final = "mixers_connected"
ATTR_MIXER_SENSORS: Final = "mixer_sensors"

MIXER_SENSOR_SIZE: Final = 8


class MixerSensorsStructure(StructureDecoder):
    """Represents a mixer sensors data structure."""

    __slots__ = ("_offset",)

    _offset: int

    def _unpack_mixer_sensors(self, message: bytearray) -> dict[str, Any] | None:
        """Unpack sensors for a mixer."""
        offset = self._offset
        current_temp = Float.from_bytes(message, offset)
        try:
            return (
                {
                    ATTR_CURRENT_TEMP: current_temp.value,
                    ATTR_TARGET_TEMP: message[offset + 4],
                    ATTR_PUMP: bool(message[offset + 6] & 0x01),
                }
                if not math.isnan(current_temp.value)
                else None
            )
        finally:
            self._offset = offset + MIXER_SENSOR_SIZE

    def _mixer_sensors(
        self, message: bytearray, mixers: int
    ) -> Generator[tuple[int, dict[str, Any]], None, None]:
        """Get sensors for a mixer."""
        for index in range(mixers):
            if sensors := self._unpack_mixer_sensors(message):
                yield (index, sensors)

    def decode(
        self, message: bytearray, offset: int = 0, data: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], int]:
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


__all__ = [
    "ATTR_PUMP",
    "ATTR_MIXERS_AVAILABLE",
    "ATTR_MIXERS_CONNECTED",
    "ATTR_MIXER_SENSORS",
    "MixerSensorsStructure",
]
