"""Contains network information dataclasses."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

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


@dataclass
class EthernetParameters:
    """Represents ethernet parameters."""

    ip: str = DEFAULT_IP
    netmask: str = DEFAULT_NETMASK
    gateway: str = DEFAULT_IP
    status: bool = False


@dataclass
class WirelessParameters(EthernetParameters):
    """Represents wireless network parameters."""

    ssid: str = ""
    encryption: int = WLAN_ENCRYPTION_NONE
    signal_quality: int = 100


@dataclass
class NetworkInfo:
    """Represents network parameters."""

    eth: EthernetParameters = EthernetParameters()
    wlan: WirelessParameters = WirelessParameters()
    server_status: bool = True
