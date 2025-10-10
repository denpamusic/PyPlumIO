"""Contains message frames."""

from __future__ import annotations

from pyplumio.const import ATTR_SENSORS, FrameType
from pyplumio.frames import Message, Structured, contains, frame_handler
from pyplumio.structures.frame_versions import FrameVersionsStructure
from pyplumio.structures.regulator_data import RegulatorDataStructure
from pyplumio.structures.sensor_data import SensorDataStructure


@frame_handler(FrameType.MESSAGE_REGULATOR_DATA, structure=RegulatorDataStructure)
class RegulatorDataMessage(Structured, Message):
    """Represents a regulator data message."""

    __slots__ = ()


@frame_handler(FrameType.MESSAGE_SENSOR_DATA)
@contains(FrameVersionsStructure, SensorDataStructure, container=ATTR_SENSORS)
class SensorDataMessage(Structured, Message):
    """Represents a sensor data message."""

    __slots__ = ()


__all__ = ["RegulatorDataMessage", "SensorDataMessage"]
