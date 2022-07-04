"""Contains connection shortcuts and version information."""
from __future__ import annotations

from pyplumio.connection import Connection, SerialConnection, TcpConnection
from pyplumio.helpers.network_info import (
    WLAN_ENCRYPTION_NONE,
    WLAN_ENCRYPTION_UNKNOWN,
    WLAN_ENCRYPTION_WEP,
    WLAN_ENCRYPTION_WPA,
    WLAN_ENCRYPTION_WPA2,
    EthernetParameters,
    WirelessParameters,
)
from pyplumio.version import __version__


def open_serial_connection(*args, **kwargs) -> SerialConnection:
    """Helper function for Serial connection."""
    return SerialConnection(*args, **kwargs)


def open_tcp_connection(*args, **kwargs) -> TcpConnection:
    """Helper function for TCP connection."""
    return TcpConnection(*args, **kwargs)


def ethernet_parameters(**kwargs) -> EthernetParameters:
    """Return instance of ethernet parameters dataclass."""
    return EthernetParameters(status=True, **kwargs)


def wireless_parameters(**kwargs) -> WirelessParameters:
    """Return instance of wireless parameters dataclass."""
    return WirelessParameters(status=True, **kwargs)


__all__ = [
    "Connection",
    "SerialConnection",
    "TcpConnection",
    "open_serial_connection",
    "open_tcp_connection",
    "ethernet_parameters",
    "wireless_parameters",
    "WLAN_ENCRYPTION_NONE",
    "WLAN_ENCRYPTION_UNKNOWN",
    "WLAN_ENCRYPTION_WEP",
    "WLAN_ENCRYPTION_WPA",
    "WLAN_ENCRYPTION_WPA2",
    "__version__",
]
