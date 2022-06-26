"""Contains message frames."""
from __future__ import annotations

from typing import Any, Dict

from pyplumio import util
from pyplumio.const import (
    DATA_BOILER_SENSORS,
    DATA_FAN_POWER,
    DATA_FUEL_CONSUMPTION,
    DATA_FUEL_LEVEL,
    DATA_LOAD,
    DATA_MODE,
    DATA_POWER,
    DATA_REGDATA,
    DATA_THERMOSTAT,
    DATA_TRANSMISSION,
)
from pyplumio.exceptions import VersionError
from pyplumio.frames import Message
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
        offset += 2
        self._data = {}
        if frame_version != self.VERSION:
            raise VersionError(f"Unknown regdata version: {frame_version}")

        _, offset = frame_versions.from_bytes(message, offset, self._data)
        self._data[DATA_REGDATA] = message[offset:]


class SensorData(Message):
    """Represents current device state."""

    frame_type: int = 0x35

    def parse_message(self, message: bytearray) -> None:
        """Parse message into data."""
        sensors: Dict[str, Any] = {}
        _, offset = frame_versions.from_bytes(message, offset=0, data=sensors)
        sensors[DATA_MODE] = message[offset]
        offset += 1
        _, offset = outputs.from_bytes(message, offset, sensors)
        _, offset = output_flags.from_bytes(message, offset, sensors)
        _, offset = temperatures.from_bytes(message, offset, sensors)
        _, offset = statuses.from_bytes(message, offset, sensors)
        _, offset = alarms.from_bytes(message, offset, sensors)
        sensors[DATA_FUEL_LEVEL] = message[offset]
        sensors[DATA_TRANSMISSION] = message[offset + 1]
        sensors[DATA_FAN_POWER] = util.unpack_float(message[offset + 2 : offset + 6])[0]
        sensors[DATA_LOAD] = message[offset + 6]
        sensors[DATA_POWER] = util.unpack_float(message[offset + 7 : offset + 11])[0]
        sensors[DATA_FUEL_CONSUMPTION] = util.unpack_float(
            message[offset + 11 : offset + 15]
        )[0]
        sensors[DATA_THERMOSTAT] = message[offset + 15]
        offset += 16
        _, offset = modules.from_bytes(message, offset, sensors)
        _, offset = lambda_sensor.from_bytes(message, offset, sensors)
        _, offset = thermostats.from_bytes(message, offset, sensors)
        _, offset = mixers.from_bytes(message, offset, sensors)

        self._data = {DATA_BOILER_SENSORS: sensors}
