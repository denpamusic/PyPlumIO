"""Contains connection shortcuts and version information."""
from __future__ import annotations

from pyplumio.connection import SerialConnection, TcpConnection
from pyplumio.version import __version__


def open_serial_connection(*args, **kwargs) -> SerialConnection:
    """Helper function for Serial connection."""
    return SerialConnection(*args, **kwargs)


def open_tcp_connection(*args, **kwargs) -> TcpConnection:
    """Helper function for TCP connection."""
    return TcpConnection(*args, **kwargs)


__all__ = [
    "SerialConnection",
    "TcpConnection",
    "open_serial_connection",
    "open_tcp_connection",
    "__version__",
]
