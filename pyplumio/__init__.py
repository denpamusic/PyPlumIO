"""Contains connection shortcuts and version information."""
from __future__ import annotations

from pyplumio._version import __version__, __version_tuple__
from pyplumio.connection import Connection, SerialConnection, TcpConnection
from pyplumio.structures.network_info import EthernetParameters, WirelessParameters


def open_serial_connection(
    device: str,
    baudrate: int = 115200,
    *,
    ethernet_parameters: EthernetParameters | None = None,
    wireless_parameters: WirelessParameters | None = None,
    reconnect_on_failure: bool = True,
    **kwargs,
) -> SerialConnection:
    """Create a serial connection."""
    return SerialConnection(
        device,
        baudrate,
        ethernet_parameters=ethernet_parameters,
        wireless_parameters=wireless_parameters,
        reconnect_on_failure=reconnect_on_failure,
        **kwargs,
    )


def open_tcp_connection(
    host: str,
    port: int,
    *,
    ethernet_parameters: EthernetParameters | None = None,
    wireless_parameters: WirelessParameters | None = None,
    reconnect_on_failure: bool = True,
    **kwargs,
) -> TcpConnection:
    """Create a TCP connection."""
    return TcpConnection(
        host,
        port,
        ethernet_parameters=ethernet_parameters,
        wireless_parameters=wireless_parameters,
        reconnect_on_failure=reconnect_on_failure,
        **kwargs,
    )


__all__ = [
    "Connection",
    "SerialConnection",
    "TcpConnection",
    "EthernetParameters",
    "WirelessParameters",
    "open_serial_connection",
    "open_tcp_connection",
    "__version__",
    "__version_tuple__",
]
