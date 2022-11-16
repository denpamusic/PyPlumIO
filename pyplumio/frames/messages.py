"""Contains message frames."""
from __future__ import annotations

from typing import ClassVar, Final

from pyplumio.const import (
    ATTR_BOILER_SENSORS,
    ATTR_MODE,
    ATTR_REGDATA,
    ATTR_THERMOSTAT,
    ATTR_TRANSMISSION,
)
from pyplumio.exceptions import VersionError
from pyplumio.frames import FrameTypes, Message
from pyplumio.helpers.typing import DeviceDataType, MessageType
from pyplumio.structures.fan_power import FanPowerStructure
from pyplumio.structures.frame_versions import FrameVersionsStructure
from pyplumio.structures.fuel_consumption import FuelConsumptionStructure
from pyplumio.structures.fuel_level import FuelLevelStructure
from pyplumio.structures.lambda_sensor import LambaSensorStructure
from pyplumio.structures.load import LoadStructure
from pyplumio.structures.mixers import MixersStructure
from pyplumio.structures.modules import ModulesStructure
from pyplumio.structures.output_flags import OutputFlagsStructure
from pyplumio.structures.outputs import OutputsStructure
from pyplumio.structures.pending_alerts import PendingAlertsStructure
from pyplumio.structures.power import PowerStructure
from pyplumio.structures.statuses import StatusesStructure
from pyplumio.structures.temperatures import TemperaturesStructure
from pyplumio.structures.thermostats import ThermostatsStructure

REGDATA_VERSION: Final = "1.0"


class RegulatorDataMessage(Message):
    """Represents current regulator data."""

    frame_type: ClassVar[int] = FrameTypes.MESSAGE_REGULATOR_DATA

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

    frame_type: ClassVar[int] = FrameTypes.MESSAGE_SENSOR_DATA

    def decode_message(self, message: MessageType) -> DeviceDataType:
        """Decode frame message."""
        sensors, offset = FrameVersionsStructure(self).decode(message, offset=0)
        sensors[ATTR_MODE] = message[offset]
        sensors, offset = OutputsStructure(self).decode(message, offset + 1, sensors)
        sensors, offset = OutputFlagsStructure(self).decode(message, offset, sensors)
        sensors, offset = TemperaturesStructure(self).decode(message, offset, sensors)
        sensors, offset = StatusesStructure(self).decode(message, offset, sensors)
        sensors, offset = PendingAlertsStructure(self).decode(message, offset, sensors)
        sensors, offset = FuelLevelStructure(self).decode(message, offset, sensors)
        sensors[ATTR_TRANSMISSION] = message[offset]
        sensors, offset = FanPowerStructure(self).decode(message, offset + 1, sensors)
        sensors, offset = LoadStructure(self).decode(message, offset, sensors)
        sensors, offset = PowerStructure(self).decode(message, offset, sensors)
        sensors, offset = FuelConsumptionStructure(self).decode(
            message, offset, sensors
        )
        sensors[ATTR_THERMOSTAT] = message[offset]
        sensors, offset = ModulesStructure(self).decode(message, offset + 1, sensors)
        sensors, offset = LambaSensorStructure(self).decode(message, offset, sensors)
        sensors, offset = ThermostatsStructure(self).decode(message, offset, sensors)
        sensors, offset = MixersStructure(self).decode(message, offset, sensors)

        return {ATTR_BOILER_SENSORS: sensors}
