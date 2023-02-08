"""Contains connection shortcuts and version information."""
from __future__ import annotations

from pyplumio.connection import Connection, SerialConnection, TcpConnection
from pyplumio.helpers.network_info import EthernetParameters, WirelessParameters
from pyplumio.version import __version__


def open_serial_connection(
    device: str, baudrate: int = 115200, **kwargs
) -> SerialConnection:
    """Helper function for Serial connection."""
    return SerialConnection(device, baudrate, **kwargs)


def open_tcp_connection(host: str, port: int, **kwargs) -> TcpConnection:
    """Helper function for TCP connection."""
    return TcpConnection(host, port, **kwargs)


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
    "__version__",
]
