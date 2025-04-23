"""Contains connection shortcuts and version information."""

from __future__ import annotations

from typing import Any

from pyplumio._version import __version__, __version_tuple__
from pyplumio.connection import SerialConnection, TcpConnection
from pyplumio.exceptions import (
    ChecksumError,
    ConnectionFailedError,
    FrameDataError,
    ProtocolError,
    PyPlumIOError,
    ReadError,
    RequestError,
    UnknownDeviceError,
    UnknownFrameError,
)
from pyplumio.frames import Frame
from pyplumio.protocol import AsyncProtocol, DummyProtocol, Protocol
from pyplumio.structures.network_info import EthernetParameters, WirelessParameters


def open_serial_connection(
    device: str,
    baudrate: int = 115200,
    *,
    protocol: Protocol | None = None,
    reconnect_on_failure: bool = True,
    **kwargs: Any,
) -> SerialConnection:
    r"""Create a serial connection.

    :param device: Serial port device name. e. g. /dev/ttyUSB0
    :type device: str
    :param baudrate: Serial port baud rate, defaults to 115200
    :type baudrate: int, optional
    :param protocol: Protocol that will be used for communication with
        the ecoMAX controller, default to AsyncProtocol
    :type protocol: Protocol, optional
    :param reconnect_on_failure: `True` if PyPlumIO should try
        reconnecting on failure, otherwise `False`, default to `True`
    :type reconnect_on_failure: bool, optional
    :param \**kwargs: Additional keyword arguments to be passed to
        serial_asyncio.open_serial_connection()
    :return: An instance of serial connection
    :rtype: SerialConnection
    """
    return SerialConnection(
        device,
        baudrate,
        protocol=protocol,
        reconnect_on_failure=reconnect_on_failure,
        **kwargs,
    )


def open_tcp_connection(
    host: str,
    port: int,
    *,
    protocol: Protocol | None = None,
    reconnect_on_failure: bool = True,
    **kwargs: Any,
) -> TcpConnection:
    r"""Create a TCP connection.

    :param host: IP address or host name of the remote RS-485 server
    :type host: str
    :param port: Port that remote RS-485 server is listening to
    :type port: int
    :param protocol: Protocol that will be used for communication with
        the ecoMAX controller, default to AsyncProtocol
    :type protocol: Protocol, optional
    :param reconnect_on_failure: `True` if PyPlumIO should try
        reconnecting on failure, otherwise `False`, default to `True`
    :type reconnect_on_failure: bool, optional
    :param \**kwargs: Additional keyword arguments to be passed to
        asyncio.open_connection()
    :return: An instance of TCP connection
    :rtype: TcpConnection
    """
    return TcpConnection(
        host,
        port,
        protocol=protocol,
        reconnect_on_failure=reconnect_on_failure,
        **kwargs,
    )


__all__ = [
    "__version__",
    "__version_tuple__",
    "AsyncProtocol",
    "ChecksumError",
    "ConnectionFailedError",
    "DummyProtocol",
    "EthernetParameters",
    "Frame",
    "FrameDataError",
    "Protocol",
    "ProtocolError",
    "PyPlumIOError",
    "ReadError",
    "RequestError",
    "SerialConnection",
    "TcpConnection",
    "UnknownDeviceError",
    "UnknownFrameError",
    "WirelessParameters",
    "open_serial_connection",
    "open_tcp_connection",
]
