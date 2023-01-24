"""Contains network information dataclasses."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from pyplumio.const import EncryptionType

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
    encryption: EncryptionType = EncryptionType.NONE
    signal_quality: int = 100


@dataclass
class NetworkInfo:
    """Represents network parameters."""

    eth: EthernetParameters = field(default_factory=EthernetParameters)
    wlan: WirelessParameters = field(default_factory=WirelessParameters)
    server_status: bool = True
