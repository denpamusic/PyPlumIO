"""Contains connection shortcuts and version information."""
from __future__ import annotations

from .connection import SerialConnection, TcpConnection
from .version import __version__

__all__ = [
    "SerialConnection",
    "TcpConnection",
    "__version__",
]
