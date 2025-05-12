"""Contains constants."""

from __future__ import annotations

from enum import Enum, IntEnum, unique
from typing import Any, Final, Literal

from typing_extensions import TypeAlias

# General attributes.
ATTR_CONNECTED: Final = "connected"
ATTR_COUNT: Final = "count"
ATTR_CURRENT_TEMP: Final = "current_temp"
ATTR_DEVICE_INDEX: Final = "device_index"
ATTR_FRAME_ERRORS: Final = "frame_errors"
ATTR_INDEX: Final = "index"
ATTR_OFFSET: Final = "offset"
ATTR_PARAMETER: Final = "parameter"
ATTR_PASSWORD: Final = "password"
ATTR_SCHEDULE: Final = "schedule"
ATTR_SETUP: Final = "setup"
ATTR_SENSORS: Final = "sensors"
ATTR_START: Final = "start"
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
    def _missing_(cls, value: Any) -> DeviceState | None:
        """Look up state in extra state table."""
        return EXTRA_DEVICE_STATES.get(value, None)


EXTRA_DEVICE_STATES: Final = {
    12: DeviceState.STABILIZATION,  # ecoMAX 810P-L TOUCH
    23: DeviceState.STABILIZATION,  # ecoMAX 860P3-O
}


@unique
class LambdaState(IntEnum):
    """Contain lambda sensor states."""

    STOP = 0
    START = 1
    WORKING = 3


@unique
class ProductType(IntEnum):
    """Contains product types."""

    ECOMAX_P = 0
    ECOMAX_I = 1


@unique
class ProductModel(Enum):
    """Contains device models."""

    ECOMAX_860D3_HB = "ecoMAX 860D3-HB"


@unique
class AlertType(IntEnum):
    """Contains alert types."""

    POWER_LOSS = 0
    BOILER_TEMP_SENSOR_FAILURE = 1
    MAX_BOILER_TEMP_EXCEEDED = 2
    FEEDER_TEMP_SENSOR_FAILURE = 3
    MAX_FEEDER_TEMP_EXCEEDED = 4
    EXHAUST_TEMP_SENSOR_FAILURE = 5
    MAX_EXHAUST_TEMP_EXCEEDED = 6
    KINDLING_FAILURE = 7
    NO_FUEL = 8
    LEAK_DETECTED = 9
    PRESSURE_SENSOR_FAILURE = 10
    FAN_FAILURE = 11
    INSUFFICIENT_AIR_PRESSURE = 12
    BURN_OFF_FAILURE = 13
    FLAME_SENSOR_FAILURE = 14
    LINEAR_ACTUATOR_BLOCKED = 15
    INCORRECT_PARAMETERS = 16
    CONDENSATION_WARNING = 17
    BOILER_STB_TRIPPED = 18
    FEEDER_STB_TRIPPED = 19
    MIN_WATER_PRESSURE_EXCEEDED = 20
    MAX_WATER_PRESSURE_EXCEEDED = 21
    FEEDER_JAMMED = 22
    FLAMEOUT = 23
    EXHAUST_FAN_FAILURE = 24
    EXTERNAL_FEEDER_FAILURE = 25
    SOLAR_COLLECTOR_TEMP_SENSOR_FAILURE = 26
    SOLAR_CIRCUIT_TEMP_SENSOR_FAILURE = 27
    H1_CIRCUIT_TEMP_SENSOR_FAILURE = 28
    H2_CIRCUIT_TEMP_SENSOR_FAILURE = 29
    H3_CIRCUIT_TEMP_SENSOR_FAILURE = 30
    OUTDOOR_TEMP_SENSOR_FAILURE = 31
    WATER_HEATER_TEMP_SENSOR_FAILURE = 32
    H0_CIRCUIT_TEMP_SENSOR_FAILURE = 33
    FROST_PROTECTION_RUNNING_WO_HS = 34
    FROST_PROTECTION_RUNNING_W_HS = 35
    MAX_SOLAR_COLLECTOR_TEMP_EXCEEDED = 36
    MAX_HEATED_FLOOR_TEMP_EXCEEDED = 37
    BOILER_COOLING_RUNNING = 38
    ECOLAMBDA_CONNECTION_FAILURE = 39
    PRIMARY_AIR_THROTTLE_JAMMED = 40
    SECONDARY_AIR_THROTTLE_JAMMED = 41
    FEEDER_OVERFLOW = 42
    FURNANCE_OVERFLOW = 43
    MODULE_B_CONNECTION_FAILURE = 44
    CLEANING_ACTUATOR_FAILURE = 45
    MIN_PRESSURE_EXCEEDED = 46
    MAX_PRESSURE_EXCEEDED = 47
    PRESSURE_SENSOR_DAMAGED = 48
    MAX_MAIN_HS_TEMP_EXCEEDED = 49
    MAX_ADDITIONAL_HS_TEMP_EXCEEDED = 50
    SOLAR_PANEL_OFFLINE = 51
    FEEDER_CONTROL_FAILURE = 52
    FEEDER_BLOCKED = 53
    MAX_THERMOCOPLE_TEMP_EXCEEDED = 54
    THERMOCOUPLE_WIRING_FAILURE = 55
    UNKNOWN_ERROR = 255


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


PERCENTAGE: Final = "%"

STATE_ON: Final = "on"
STATE_OFF: Final = "off"
State: TypeAlias = Literal["on", "off"]
