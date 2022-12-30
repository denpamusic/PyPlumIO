"""Contains constants."""
from __future__ import annotations

from enum import IntEnum, unique
from typing import Final

STATE_ON: Final = "on"
STATE_OFF: Final = "off"

ATTR_INDEX: Final = "index"
ATTR_VALUE: Final = "value"
ATTR_EXTRA: Final = "extra"
ATTR_ECOMAX_SENSORS: Final = "sensors"
ATTR_ECOMAX_PARAMETERS: Final = "parameters"
ATTR_PENDING_ALERTS: Final = "pending_alerts"
ATTR_ALERTS: Final = "alerts"
ATTR_FAN_POWER: Final = "fan_power"
ATTR_FRAME_VERSIONS: Final = "frames"
ATTR_FUEL_CONSUMPTION: Final = "fuel_consumption"
ATTR_FUEL_LEVEL: Final = "fuel_level"
ATTR_FUEL_BURNED: Final = "fuel_burned"
ATTR_LOAD: Final = "load"
ATTR_MIXERS: Final = "mixers"
ATTR_MIXERS_NUMBER: Final = "mixers_number"
ATTR_MIXER_SENSORS: Final = "mixer_sensors"
ATTR_MIXER_PARAMETERS: Final = "mixer_parameters"
ATTR_STATE: Final = "state"
ATTR_MODULES: Final = "modules"
ATTR_POWER: Final = "power"
ATTR_THERMOSTAT: Final = "thermostat"
ATTR_THERMOSTATS: Final = "thermostats"
ATTR_THERMOSTATS_NUMBER: Final = "thermostats_number"
ATTR_THERMOSTAT_SENSORS: Final = "thermostat_sensors"
ATTR_THERMOSTAT_PARAMETERS: Final = "thermostat_parameters"
ATTR_THERMOSTAT_PARAMETERS_DECODER: Final = "thermostat_parameters_decoder"
ATTR_TRANSMISSION: Final = "transmission"
ATTR_PRODUCT: Final = "product"
ATTR_NETWORK: Final = "network"
ATTR_VERSION: Final = "version"
ATTR_PASSWORD: Final = "password"
ATTR_SCHEMA: Final = "schema"
ATTR_REGDATA: Final = "regdata"
ATTR_REGDATA_DECODER: Final = "regdata_decoder"
ATTR_LAMBDA_SENSOR: Final = "lambda"
ATTR_SCHEDULES: Final = "schedules"
ATTR_TYPE: Final = "type"
ATTR_SWITCH: Final = "switch"
ATTR_PARAMETER: Final = "parameter"
ATTR_SCHEDULE: Final = "schedule"

BYTE_UNDEFINED: Final = 0xFF


@unique
class DeviceState(IntEnum):
    """Contains device states."""

    OFF = 0
    FANNING = 1
    KINDLING = 2
    WORKING = 3
    SUPERVISION = 4
    PAUSED = 5
    STANDBY = 6
    BURNING_OFF = 7
    ALERT = 8
    MANUAL = 9
    UNSEALING = 10
    OTHER = 11


@unique
class DeviceType(IntEnum):
    """Contains device addresses."""

    ALL = 0
    ECOMAX = 69
    ECOSTER = 81
    ECONET = 86


@unique
class FrameType(IntEnum):
    """Contains frame types."""

    REQUEST_STOP_MASTER = 24
    REQUEST_START_MASTER = 25
    REQUEST_CHECK_DEVICE = 48
    REQUEST_ECOMAX_PARAMETERS = 49
    REQUEST_MIXER_PARAMETERS = 50
    REQUEST_SET_ECOMAX_PARAMETER = 51
    REQUEST_SET_MIXER_PARAMETER = 52
    REQUEST_SCHEDULES = 54
    REQUEST_SET_SCHEDULE = 55
    REQUEST_UID = 57
    REQUEST_PASSWORD = 58
    REQUEST_ECOMAX_CONTROL = 59
    REQUEST_ALERTS = 61
    REQUEST_PROGRAM_VERSION = 64
    REQUEST_DATA_SCHEMA = 85
    REQUEST_THERMOSTAT_PARAMETERS = 92
    REQUEST_SET_THERMOSTAT_PARAMETER = 93
    RESPONSE_DEVICE_AVAILABLE = 176
    RESPONSE_ECOMAX_PARAMETERS = 177
    RESPONSE_MIXER_PARAMETERS = 178
    RESPONSE_SET_ECOMAX_PARAMETER = 179
    RESPONSE_SET_MIXER_PARAMETER = 180
    RESPONSE_SCHEDULES = 182
    RESPONSE_UID = 185
    RESPONSE_PASSWORD = 186
    RESPONSE_ECOMAX_CONTROL = 187
    RESPONSE_ALERTS = 189
    RESPONSE_PROGRAM_VERSION = 192
    RESPONSE_DATA_SCHEMA = 213
    RESPONSE_THERMOSTAT_PARAMETERS = 220
    RESPONSE_SET_THERMOSTAT_PARAMETER = 221
    MESSAGE_REGULATOR_DATA = 8
    MESSAGE_SENSOR_DATA = 53
