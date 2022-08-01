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
from pyplumio.structures.frame_versions import FrameVersionsStructure
from pyplumio.structures.lambda_sensor import LambaSensorStructure
from pyplumio.structures.mixers import MixersStructure
from pyplumio.structures.modules import ModulesStructure
from pyplumio.structures.output_flags import OutputFlagsStructure
from pyplumio.structures.outputs import OutputsStructure
from pyplumio.structures.pending_alerts import PendingAlertsStructure
from pyplumio.structures.statuses import StatusesStructure
from pyplumio.structures.temperatures import TemperaturesStructure
from pyplumio.structures.thermostats import ThermostatsStructure

REGDATA_VERSION: Final = "1.0"


class RegulatorDataMessage(Message):
    """Represents current regulator data."""

    frame_type: ClassVar[int] = MessageTypes.REGULATOR_DATA

    def decode_message(self, message: MessageType) -> DeviceDataType:
        """Decode frame message."""
        offset = 2
        frame_version = f"{message[offset+1]}.{message[offset]}"
        if frame_version != REGDATA_VERSION:
            raise VersionError(f"Unknown regdata version ({frame_version})")

        data, offset = FrameVersionsStructure(self).decode(message, offset + 2)
        data[ATTR_REGDATA] = message[offset:]

        return data


class SensorDataMessage(Message):
    """Represents current device state."""

    frame_type: ClassVar[int] = MessageTypes.SENSOR_DATA

    def decode_message(self, message: MessageType) -> DeviceDataType:
        """Decode frame message."""
        sensors, offset = FrameVersionsStructure(self).decode(message, offset=0)
        sensors[ATTR_MODE] = message[offset]
        sensors, offset = OutputsStructure(self).decode(message, offset + 1, sensors)
        sensors, offset = OutputFlagsStructure(self).decode(message, offset, sensors)
        sensors, offset = TemperaturesStructure(self).decode(message, offset, sensors)
        sensors, offset = StatusesStructure(self).decode(message, offset, sensors)
        sensors, offset = PendingAlertsStructure(self).decode(message, offset, sensors)
        sensors[ATTR_FUEL_LEVEL] = message[offset]
        sensors[ATTR_TRANSMISSION] = message[offset + 1]
        sensors[ATTR_FAN_POWER] = util.unpack_float(message[offset + 2 : offset + 6])[0]
        sensors[ATTR_LOAD] = message[offset + 6]
        sensors[ATTR_POWER] = util.unpack_float(message[offset + 7 : offset + 11])[0]
        sensors[ATTR_FUEL_CONSUMPTION] = util.unpack_float(
            message[offset + 11 : offset + 15]
        )[0]
        sensors[ATTR_THERMOSTAT] = message[offset + 15]
        sensors, offset = ModulesStructure(self).decode(message, offset + 16, sensors)
        sensors, offset = LambaSensorStructure(self).decode(message, offset, sensors)
        sensors, offset = ThermostatsStructure(self).decode(message, offset, sensors)
        sensors, offset = MixersStructure(self).decode(message, offset, sensors)

        return {ATTR_BOILER_SENSORS: sensors}
