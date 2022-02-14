"""Contains connection shortcuts and version information."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Awaitable

from .connection import Connection, SerialConnection, TcpConnection
from .devices import DevicesCollection
from .version import __version__  # noqa


def tcp(
    callback: Callable[[DevicesCollection, Connection], Awaitable[Any]],
    host: str,
    port: int,
    interval: int = 1,
    **kwargs,
) -> None:
    """Shortcut for TCP connection.

    Keyword arguments:
        callback -- callback method
        host -- device host
        port -- device port
        interval -- callback update interval in seconds
        **kwargs -- keyword arguments for connection driver
    """
    TcpConnection(host, port, **kwargs).run(callback, interval)


def serial(
    callback: Callable[[DevicesCollection, Connection], Awaitable[Any]],
    device: str,
    baudrate: int = 115200,
    interval: int = 1,
    **kwargs,
) -> None:
    """Shortcut for serial connection.

    Keyword arguments:
        callback -- callback method
        device -- serial device url, e. g. /dev/ttyUSB0
        baudrate -- serial port baudrate
        interval -- callback update interval in seconds
        **kwargs -- keyword arguments for connection driver
    """
    SerialConnection(device, baudrate, **kwargs).run(callback, interval)
