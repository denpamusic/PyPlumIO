"""Contains message frames."""
from __future__ import annotations

from typing import ClassVar, Final

from pyplumio import util
from pyplumio.const import (
    ATTR_BOILER_SENSORS,
    ATTR_FAN_POWER,
    ATTR_FUEL_CONSUMPTION,
    ATTR_FUEL_LEVEL,
    ATTR_LOAD,
    ATTR_MODE,
    ATTR_POWER,
    ATTR_REGDATA,
    ATTR_THERMOSTAT,
    ATTR_TRANSMISSION,
)
from pyplumio.exceptions import VersionError
from pyplumio.frames import Message, MessageTypes
from pyplumio.helpers.typing import DeviceDataType, MessageType
from pyplumio.structures import (
    alarms,
    frame_versions,
    lambda_sensor,
    mixers,
    modules,
    output_flags,
    outputs,
    statuses,
    temperatures,
    thermostats,
)

REGDATA_VERSION: Final = "1.0"


class RegulatorDataMessage(Message):
    """Represents current regulator data."""

    frame_type: ClassVar[int] = MessageTypes.REGULATOR_DATA

    def decode_message(self, message: MessageType) -> DeviceDataType:
        """Decode frame message."""
        offset = 2
        frame_version = f"{message[offset+1]}.{message[offset]}"
        if frame_version != REGDATA_VERSION:
            raise VersionError(f"unknown regdata version {frame_version}")

        data, offset = frame_versions.from_bytes(message, offset + 2)
        data[ATTR_REGDATA] = message[offset:]

        return data


class SensorDataMessage(Message):
    """Represents current device state."""

    frame_type: ClassVar[int] = MessageTypes.SENSOR_DATA

    def decode_message(self, message: MessageType) -> DeviceDataType:
        """Decode frame message."""
        sensors: DeviceDataType = {}
        _, offset = frame_versions.from_bytes(message, offset=0, data=sensors)
        sensors[ATTR_MODE] = message[offset]
        _, offset = outputs.from_bytes(message, offset + 1, sensors)
        _, offset = output_flags.from_bytes(message, offset, sensors)
        _, offset = temperatures.from_bytes(message, offset, sensors)
        _, offset = statuses.from_bytes(message, offset, sensors)
        _, offset = alarms.from_bytes(message, offset, sensors)
        sensors[ATTR_FUEL_LEVEL] = message[offset]
        sensors[ATTR_TRANSMISSION] = message[offset + 1]
        sensors[ATTR_FAN_POWER] = util.unpack_float(message[offset + 2 : offset + 6])[0]
        sensors[ATTR_LOAD] = message[offset + 6]
        sensors[ATTR_POWER] = util.unpack_float(message[offset + 7 : offset + 11])[0]
        sensors[ATTR_FUEL_CONSUMPTION] = util.unpack_float(
            message[offset + 11 : offset + 15]
        )[0]
        sensors[ATTR_THERMOSTAT] = message[offset + 15]
        _, offset = modules.from_bytes(message, offset + 16, sensors)
        _, offset = lambda_sensor.from_bytes(message, offset, sensors)
        _, offset = thermostats.from_bytes(message, offset, sensors)
        _, offset = mixers.from_bytes(message, offset, sensors)

        return {ATTR_BOILER_SENSORS: sensors}
