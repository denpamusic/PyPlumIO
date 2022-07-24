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
from pyplumio.structures.current_alerts import CurrentAlertsStructure
from pyplumio.structures.frame_versions import FrameVersionStructure
from pyplumio.structures.lambda_sensor import LambaSensorStructure
from pyplumio.structures.mixers import MixersStructure
from pyplumio.structures.modules import ModulesStructure
from pyplumio.structures.output_flags import OutputFlagsStructure
from pyplumio.structures.outputs import OutputsStructure
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
            raise VersionError(f"unknown regdata version {frame_version}")

        data, offset = FrameVersionStructure(self).decode(message, offset + 2)
        data[ATTR_REGDATA] = message[offset:]

        return data


class SensorDataMessage(Message):
    """Represents current device state."""

    frame_type: ClassVar[int] = MessageTypes.SENSOR_DATA

    def decode_message(self, message: MessageType) -> DeviceDataType:
        """Decode frame message."""
        sensors: DeviceDataType = {}

        offset = FrameVersionStructure(self).decode(message, offset=0, data=sensors)[1]
        sensors[ATTR_MODE] = message[offset]
        offset = OutputsStructure(self).decode(message, offset + 1, sensors)[1]
        offset = OutputFlagsStructure(self).decode(message, offset, sensors)[1]
        offset = TemperaturesStructure(self).decode(message, offset, sensors)[1]
        offset = StatusesStructure(self).decode(message, offset, sensors)[1]
        offset = CurrentAlertsStructure(self).decode(message, offset, sensors)[1]
        sensors[ATTR_FUEL_LEVEL] = message[offset]
        sensors[ATTR_TRANSMISSION] = message[offset + 1]
        sensors[ATTR_FAN_POWER] = util.unpack_float(message[offset + 2 : offset + 6])[0]
        sensors[ATTR_LOAD] = message[offset + 6]
        sensors[ATTR_POWER] = util.unpack_float(message[offset + 7 : offset + 11])[0]
        sensors[ATTR_FUEL_CONSUMPTION] = util.unpack_float(
            message[offset + 11 : offset + 15]
        )[0]
        sensors[ATTR_THERMOSTAT] = message[offset + 15]
        offset = ModulesStructure(self).decode(message, offset + 16, sensors)[1]
        offset = LambaSensorStructure(self).decode(message, offset, sensors)[1]
        offset = ThermostatsStructure(self).decode(message, offset, sensors)[1]
        offset = MixersStructure(self).decode(message, offset, sensors)[1]

        return {ATTR_BOILER_SENSORS: sensors}
