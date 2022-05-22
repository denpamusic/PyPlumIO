"""Test PyPlumIO init."""

from unittest.mock import AsyncMock, patch

import pyplumio


def test_tcp():
    """Test tcp helper function."""
    callback = AsyncMock()

    with patch(
        "pyplumio.TcpConnection.__init__",
        return_value=None,
    ) as mock_init_func, patch(
        "pyplumio.TcpConnection.run", return_value=True
    ) as mock_run_function:
        pyplumio.tcp(callback, host="1.1.1.1", port=8888, interval=5)

    mock_init_func.assert_called_once_with("1.1.1.1", 8888)
    mock_run_function.assert_called_once_with(callback, 5)


def test_serial():
    """Test serial helper function."""
    callback = AsyncMock()

    with patch(
        "pyplumio.SerialConnection.__init__",
        return_value=None,
    ) as mock_init_func, patch(
        "pyplumio.SerialConnection.run",
        return_value=True,
    ) as mock_run_func:
        pyplumio.serial(callback, device="/dev/ttyUSB0", baudrate=9600, interval=5)

    mock_init_func.assert_called_once_with("/dev/ttyUSB0", 9600)
    mock_run_func.assert_called_once_with(callback, 5)
