"""Contains message frames."""
from __future__ import annotations

from typing import ClassVar

from pyplumio.const import (
    ATTR_SENSORS,
    ATTR_STATE,
    ATTR_THERMOSTAT,
    ATTR_TRANSMISSION,
    DeviceState,
    FrameType,
)
from pyplumio.frames import Message
from pyplumio.helpers.typing import DeviceDataType, MessageType
from pyplumio.structures.fan_power import FanPowerStructure
from pyplumio.structures.frame_versions import FrameVersionsStructure
from pyplumio.structures.fuel_consumption import FuelConsumptionStructure
from pyplumio.structures.fuel_level import FuelLevelStructure
from pyplumio.structures.lambda_sensor import LambaSensorStructure
from pyplumio.structures.load import LoadStructure
from pyplumio.structures.mixer_sensors import MixerSensorsStructure
from pyplumio.structures.modules import ModulesStructure
from pyplumio.structures.output_flags import OutputFlagsStructure
from pyplumio.structures.outputs import OutputsStructure
from pyplumio.structures.pending_alerts import PendingAlertsStructure
from pyplumio.structures.power import PowerStructure
from pyplumio.structures.regulator_data import (
    ATTR_REGDATA_DECODER,
    RegulatorDataStructure,
)
from pyplumio.structures.statuses import StatusesStructure
from pyplumio.structures.temperatures import TemperaturesStructure
from pyplumio.structures.thermostat_sensors import ThermostatSensorsStructure


class RegulatorDataMessage(Message):
    """Represents current regulator data."""

    frame_type: ClassVar[int] = FrameType.MESSAGE_REGULATOR_DATA

    def decode_message(self, message: MessageType) -> DeviceDataType:
        """Decode frame message."""
        return {ATTR_REGDATA_DECODER: RegulatorDataStructure(self)}


class SensorDataMessage(Message):
    """Represents current device state."""

    frame_type: ClassVar[int] = FrameType.MESSAGE_SENSOR_DATA

    def decode_message(self, message: MessageType) -> DeviceDataType:
        """Decode frame message."""
        sensors, offset = FrameVersionsStructure(self).decode(message, offset=0)
        try:
            sensors[ATTR_STATE] = message[offset]
            sensors[ATTR_STATE] = DeviceState(sensors[ATTR_STATE])
        except ValueError:
            pass

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
        sensors, offset = ThermostatSensorsStructure(self).decode(
            message, offset, sensors
        )
        sensors, offset = MixerSensorsStructure(self).decode(message, offset, sensors)

        return {ATTR_SENSORS: sensors}
