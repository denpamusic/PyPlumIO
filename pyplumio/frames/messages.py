"""Contains message frames."""
from __future__ import annotations

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
from pyplumio.frames import Message
from pyplumio.helpers.typing import DeviceData
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


class RegulatorData(Message):
    """Represents current regulator data."""

    frame_type: int = 0x08
    VERSION: str = "1.0"

    def parse_message(self, message: bytearray) -> None:
        """Parse message into data."""
        offset = 2
        frame_version = f"{message[offset+1]}.{message[offset]}"
        self._data = {}
        if frame_version != self.VERSION:
            raise VersionError(f"Unknown regdata version: {frame_version}")

        _, offset = frame_versions.from_bytes(message, offset + 2, self._data)
        self._data[ATTR_REGDATA] = message[offset:]


class SensorData(Message):
    """Represents current device state."""

    frame_type: int = 0x35

    def parse_message(self, message: bytearray) -> None:
        """Parse message into data."""
        sensors: DeviceData = {}
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

        self._data = {ATTR_BOILER_SENSORS: sensors}
