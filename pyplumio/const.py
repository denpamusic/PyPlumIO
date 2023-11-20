"""Contains constants."""
from __future__ import annotations

from enum import Enum, IntEnum, unique
from typing import Final

UNDEFINED: Final = "undefined"

# Binary states.
STATE_ON: Final = "on"
STATE_OFF: Final = "off"

# General attributes.
ATTR_CONNECTED: Final = "connected"
ATTR_COUNT: Final = "count"
ATTR_CURRENT_TEMP: Final = "current_temp"
ATTR_DEVICE_INDEX: Final = "device_index"
ATTR_FRAME_ERRORS: Final = "frame_errors"
ATTR_INDEX: Final = "index"
ATTR_LOADED: Final = "loaded"
ATTR_OFFSET: Final = "offset"
ATTR_PARAMETER: Final = "parameter"
ATTR_PASSWORD: Final = "password"
ATTR_SCHEDULE: Final = "schedule"
ATTR_SENSORS: Final = "sensors"
ATTR_STATE: Final = "state"
ATTR_SWITCH: Final = "switch"
ATTR_TARGET_TEMP: Final = "target_temp"
ATTR_THERMOSTAT: Final = "thermostat"
ATTR_TRANSMISSION: Final = "transmission"
ATTR_TYPE: Final = "type"
ATTR_VALUE: Final = "value"
ATTR_SIZE: Final = "size"

# Bytes.
BYTE_UNDEFINED: Final = 0xFF


@unique
class EncryptionType(IntEnum):
    """Contains wireless encryption types."""

    UNKNOWN = 0
    NONE = 1
    WEP = 2
    WPA = 3
    WPA2 = 4


EXTRA_STATES: Final = (
    12,  # STABILIZATION: ecoMAX 810P-L TOUCH
    23,  # STABILIZATION: ecoMAX 860P3-O
)


@unique
class DeviceState(IntEnum):
    """Contains device states."""

    OFF = 0
    STABILIZATION = 1
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

    @classmethod
    def _missing_(cls, value):
        """Look up state in extra state table.

        Currently it's only used for stabilization state,
        since it differs between models.
        """
        if value in EXTRA_STATES:
            return cls.STABILIZATION

        return None


@unique
class ProductType(IntEnum):
    """Contains product types."""

    ECOMAX_P = 0
    ECOMAX_I = 1


@unique
class AlertType(IntEnum):
    """Contains alert types."""

    POWER_LOSS = 0
    BOILER_TEMP_SENSOR_FAILURE = 1
    MAX_BOILER_TEMP_EXCEEDED = 2
    FEEDER_TEMP_SENSOR_FAILURE = 3
    MAX_FEEDER_TEMP_EXCEEDED = 4
    EXHAUST_TEMP_SENSOR_FAILURE = 5
    KINDLING_FAILURE = 7
    FAN_FAILURE = 11


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
    REQUEST_REGULATOR_DATA_SCHEMA = 85
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
    RESPONSE_REGULATOR_DATA_SCHEMA = 213
    RESPONSE_THERMOSTAT_PARAMETERS = 220
    RESPONSE_SET_THERMOSTAT_PARAMETER = 221
    MESSAGE_REGULATOR_DATA = 8
    MESSAGE_SENSOR_DATA = 53


PERCENTAGE: Final = "%"


@unique
class UnitOfMeasurement(Enum):
    """Contains units of measurement."""

    CELSIUS = "°C"
    KILO_WATT = "kW"
    GRAMS = "g"
    KILOGRAMS = "kg"
    KILO_WATT_HOUR_PER_KILOGRAM = "kWh/kg"
    KILOGRAMS_PER_HOUR = "kg/h"
    SECONDS = "s"
    MINUTES = "min"
    DAYS = "days"
