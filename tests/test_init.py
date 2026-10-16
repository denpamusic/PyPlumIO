"""Contains tests for the init module."""

import importlib
from importlib.metadata import PackageNotFoundError
from typing import Final
from unittest.mock import patch

import pyplumio
from pyplumio import SerialConnection, __version__, serial_for_url, version

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
    serial_connection = serial_for_url(URL, baudrate=9600)
    assert isinstance(serial_connection, SerialConnection)
    assert serial_connection.url == URL
    assert serial_connection.options["baudrate"] == 9600
