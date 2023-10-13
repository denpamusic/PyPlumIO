"""Contains connection shortcuts and version information."""
from __future__ import annotations

from pyplumio._version import __version__, __version_tuple__
from pyplumio.connection import Connection, SerialConnection, TcpConnection
from pyplumio.structures.network_info import EthernetParameters, WirelessParameters


def open_serial_connection(
    device: str, baudrate: int = 115200, **kwargs
) -> SerialConnection:
    """Open a serial connection."""
    return SerialConnection(device, baudrate, **kwargs)


def open_tcp_connection(host: str, port: int, **kwargs) -> TcpConnection:
    """Open a TCP connection."""
    return TcpConnection(host, port, **kwargs)


def ethernet_parameters(**kwargs) -> EthernetParameters:
    """Return an instance of ethernet parameters dataclass."""
    return EthernetParameters(status=True, **kwargs)


def wireless_parameters(**kwargs) -> WirelessParameters:
    """Return an instance of wireless parameters dataclass."""
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
    "__version_tuple__",
]
