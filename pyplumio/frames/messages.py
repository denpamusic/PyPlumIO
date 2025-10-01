"""Contains message frames."""

from __future__ import annotations

from typing import Any

from pyplumio.const import ATTR_SENSORS, FrameType
from pyplumio.frames import Message
from pyplumio.structures.frame_versions import FrameVersionsStructure
from pyplumio.structures.regulator_data import RegulatorDataStructure
from pyplumio.structures.sensor_data import SensorDataStructure


class RegulatorDataMessage(Message):
    """Represents a regulator data message."""

    __slots__ = ()

    frame_type = FrameType.MESSAGE_REGULATOR_DATA

    def decode_message(self, message: bytearray) -> dict[str, Any]:
        """Decode a frame message."""
        return RegulatorDataStructure(self).decode(message)[0]


class SensorDataMessage(Message):
    """Represents a sensor data message."""

    __slots__ = ()

    frame_type = FrameType.MESSAGE_SENSOR_DATA

    def decode_message(self, message: bytearray) -> dict[str, Any]:
        """Decode a frame message."""
        sensors, offset = FrameVersionsStructure(self).decode(message, offset=0)
        sensors, offset = SensorDataStructure(self).decode(
            message, offset, data=sensors
        )
        return {ATTR_SENSORS: sensors}


__all__ = ["RegulatorDataMessage", "SensorDataMessage"]
