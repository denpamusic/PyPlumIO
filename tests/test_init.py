"""Contains tests for the init module."""

import importlib
from importlib.metadata import PackageNotFoundError
from typing import Final
from unittest.mock import patch

import pyplumio
from pyplumio import (
    SerialConnection,
    TcpConnection,
    __version__,
    open_serial_connection,
    open_tcp_connection,
    version,
)

URL: Final = "/dev/ttyUSB0"
IP: Final = "1.1.1.1"


def test_version() -> None:
    """Test package version."""
    assert __version__ == "0.7.0"
    assert version == __version__


def test_version_not_found() -> None:
    """Test version when package is not installed."""
    with patch("importlib.metadata.version", side_effect=PackageNotFoundError):
        importlib.reload(pyplumio)
        assert pyplumio.__version__ == "unknown"

    # Reload again to restore version
    importlib.reload(pyplumio)
    assert pyplumio.__version__ == "0.7.0"


def test_connection_helpers() -> None:
    """Test open connection helpers."""
    serial_connection = open_serial_connection(URL, baudrate=9600)
    assert isinstance(serial_connection, SerialConnection)
    assert serial_connection.url == URL
    assert serial_connection.baudrate == 9600
    tcp_connection = open_tcp_connection(IP, port=3939)
    assert isinstance(tcp_connection, TcpConnection)
    assert tcp_connection.host == IP
    assert tcp_connection.port == 3939
