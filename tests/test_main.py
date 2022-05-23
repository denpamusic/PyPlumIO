"""Test PyPlumIO main module."""

from unittest.mock import Mock, patch

import pytest


@pytest.mark.asyncio
async def test_main(bypass_serial_asyncio_connection, capsys) -> None:
    """Test main module."""
    with patch(
        "pyplumio.serial",
    ) as mock_serial:
        import pyplumio.__main__

    mock_serial.assert_called_once_with(
        pyplumio.__main__.main, device="/dev/ttyUSB0", baudrate=115200, interval=1
    )

    # Test callback function.
    devices = Mock()
    devices.ecomax = "test"
    connection = Mock()
    await pyplumio.__main__.main(devices, connection)
    captured = capsys.readouterr()
    assert captured.out == "test\n"
