"""Contains constants."""

from typing import Final

BROADCAST_ADDRESS: Final = 0x00
ECONET_ADDRESS: Final = 0x56
ECOMAX_ADDRESS: Final = 0x45
ECOSTER_ADDRESS: Final = 0x51

WLAN_ENCRYPTION_UNKNOWN: Final = 0
WLAN_ENCRYPTION_NONE: Final = 1
WLAN_ENCRYPTION_WEP: Final = 2
WLAN_ENCRYPTION_WPA: Final = 3
WLAN_ENCRYPTION_WPA2: Final = 4
WLAN_ENCRYPTION: Final = (
    WLAN_ENCRYPTION_UNKNOWN,
    WLAN_ENCRYPTION_NONE,
    WLAN_ENCRYPTION_WEP,
    WLAN_ENCRYPTION_WPA,
    WLAN_ENCRYPTION_WPA2,
)

DEFAULT_IP: Final = "0.0.0.0"
DEFAULT_NETMASK: Final = "255.255.255.0"

DATA_ALARMS: Final = "alarms"
DATA_FAN_POWER: Final = "fan_power"
DATA_FRAME_VERSIONS: Final = "frames"
DATA_FUEL_CONSUMPTION: Final = "fuel_consumption"
DATA_FUEL_LEVEL: Final = "fuel_level"
DATA_LOAD: Final = "load"
DATA_MIXERS: Final = "mixers"
DATA_MODE: Final = "mode"
DATA_POWER: Final = "power"
DATA_THERMOSTAT: Final = "thermostat"
DATA_THERMOSTATS: Final = "thermostats"
DATA_TRANSMISSION: Final = "transmission"
