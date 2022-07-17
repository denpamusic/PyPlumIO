"""Contains constants."""
from __future__ import annotations

from typing import Final

BROADCAST_ADDRESS: Final[int] = 0x00
ECONET_ADDRESS: Final[int] = 0x56
ECOMAX_ADDRESS: Final[int] = 0x45
ECOSTER_ADDRESS: Final[int] = 0x51

DATA_BOILER_SENSORS: Final = "sensors"
DATA_BOILER_PARAMETERS: Final = "parameters"
DATA_ALARMS: Final = "alarms"
DATA_FAN_POWER: Final = "fan_power"
DATA_FRAME_VERSIONS: Final = "frames"
DATA_FUEL_CONSUMPTION: Final = "fuel_consumption"
DATA_FUEL_LEVEL: Final = "fuel_level"
DATA_FUEL_BURNED: Final = "fuel_burned"
DATA_LOAD: Final = "load"
DATA_MIXER_SENSORS: Final = "mixer_sensors"
DATA_MIXER_PARAMETERS: Final = "mixer_parameters"
DATA_MODE: Final = "mode"
DATA_MODULES: Final = "modules"
DATA_POWER: Final = "power"
DATA_THERMOSTAT: Final = "thermostat"
DATA_THERMOSTATS: Final = "thermostats"
DATA_TRANSMISSION: Final = "transmission"
DATA_UNKNOWN: Final = "unknown"
DATA_PRODUCT: Final = "product"
DATA_NETWORK: Final = "network"
DATA_VERSION: Final = "version"
DATA_PASSWORD: Final = "password"
DATA_SCHEMA: Final = "schema"
DATA_REGDATA: Final = "regdata"
DATA_LAMBDA_SENSOR: Final = "lambda"

STATE_ON: Final = "on"
STATE_OFF: Final = "off"
