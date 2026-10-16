"""Contains connection shortcuts and version information."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _pkg_version
from typing import Any

from pyplumio.connection import SerialConnection
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

try:
    __version__ = _pkg_version("PyPlumIO")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"

version = __version__


def serial_for_url(
    url: str,
    *,
    protocol: Protocol | None = None,
    reconnect_on_failure: bool = True,
    **options: Any,
) -> SerialConnection:
    r"""Create a serial connection.

    :param url: Serial port device url. e. g. /dev/ttyUSB0 or socket://localhost:8888
    :type url: str
    :param protocol: Protocol that will be used for communication with
        the ecoMAX controller, default to AsyncProtocol
    :type protocol: Protocol, optional
    :param reconnect_on_failure: `True` if PyPlumIO should try
        reconnecting on failure, otherwise `False`, default to `True`
    :type reconnect_on_failure: bool, optional
    :param \**options: Additional arguments to be passed to
        serialx.open_serial_connection()
    :return: An instance of serial connection
    :rtype: SerialConnection
    """
    return SerialConnection(
        url,
        protocol=protocol,
        reconnect_on_failure=reconnect_on_failure,
        **options,
    )


__all__ = [
    "__version__",
    "version",
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
    "UnknownDeviceError",
    "UnknownFrameError",
    "WirelessParameters",
    "serial_for_url",
]
