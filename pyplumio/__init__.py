"""Contains connection shortcuts and version information."""
from __future__ import annotations

from pyplumio._version import __version__, __version_tuple__
from pyplumio.connection import Connection, SerialConnection, TcpConnection
from pyplumio.protocol import AsyncProtocol, Protocol
from pyplumio.structures.network_info import EthernetParameters, WirelessParameters


def open_serial_connection(
    device: str,
    baudrate: int = 115200,
    *,
    ethernet_parameters: EthernetParameters | None = None,
    wireless_parameters: WirelessParameters | None = None,
    reconnect_on_failure: bool = True,
    protocol: type[Protocol] = AsyncProtocol,
    **kwargs,
) -> SerialConnection:
    r"""Create a serial connection.

    :param device: Serial port device name. e. g. /dev/ttyUSB0
    :type device: str
    :param baudrate: Serial port baud rate, defaults to 115200
    :type baudrate: int, optional
    :param ethernet_parameters: Ethernet parameters to send to an
        ecoMAX controller
    :type ethernet_parameters: EthernetParameters, optional
    :param wireless_parameters: Wireless parameters to send to an
        ecoMAX controller
    :type wireless_parameters: WirelessParameters, optional
    :param reconnect_on_failure: `True` if PyPlumIO should try
        reconnecting on failure, otherwise `False`, default to `True`
    :type reconnect_on_failure: bool, optional
    :param protocol: Protocol that will be used for communication with
        the ecoMAX controller, default to AsyncProtocol
    :type protocol: Protocol, optional
    :param \**kwargs: Additional keyword arguments to be passed to
        serial_asyncio.open_serial_connection()
    :return: An instance of serial connection
    :rtype: SerialConnection
    """
    return SerialConnection(
        device,
        baudrate,
        ethernet_parameters=ethernet_parameters,
        wireless_parameters=wireless_parameters,
        reconnect_on_failure=reconnect_on_failure,
        protocol=protocol,
        **kwargs,
    )


def open_tcp_connection(
    host: str,
    port: int,
    *,
    ethernet_parameters: EthernetParameters | None = None,
    wireless_parameters: WirelessParameters | None = None,
    reconnect_on_failure: bool = True,
    protocol: type[Protocol] = AsyncProtocol,
    **kwargs,
) -> TcpConnection:
    r"""Create a TCP connection.

    :param host: IP address or host name of the remote RS-485 server
    :type host: str
    :param port: Port that remote RS-485 server is listening to
    :type port: int
    :param ethernet_parameters: Ethernet parameters to send to an
        ecoMAX controller
    :type ethernet_parameters: EthernetParameters, optional
    :param wireless_parameters: Wireless parameters to send to an
        ecoMAX controller
    :type wireless_parameters: WirelessParameters, optional
    :param reconnect_on_failure: `True` if PyPlumIO should try
        reconnecting on failure, otherwise `False`, default to `True`
    :type reconnect_on_failure: bool, optional
    :param protocol: Protocol that will be used for communication with
        the ecoMAX controller, default to AsyncProtocol
    :type protocol: Protocol, optional
    :param \**kwargs: Additional keyword arguments to be passed to
        asyncio.open_connection()
    :return: An instance of TCP connection
    :rtype: TcpConnection
    """
    return TcpConnection(
        host,
        port,
        ethernet_parameters=ethernet_parameters,
        wireless_parameters=wireless_parameters,
        reconnect_on_failure=reconnect_on_failure,
        protocol=protocol,
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
