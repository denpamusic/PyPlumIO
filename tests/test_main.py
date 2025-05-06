"""Contains tests for the main module."""

from unittest.mock import AsyncMock, call, patch

from pyplumio.devices import PhysicalDevice

with patch("asyncio.run") as mock_asyncio_run:
    from pyplumio.__main__ import main


async def test_main(capsys) -> None:
    """Test main."""
    mock_device = AsyncMock(spec=PhysicalDevice)
    mock_device.get.side_effect = ("one", "two")
    mock_connection = AsyncMock()
    mock_connection.__aenter__.return_value = mock_connection
    mock_connection.get.return_value = mock_device
    main_fn = mock_asyncio_run.call_args[0][0]

    with patch(
        "pyplumio.open_serial_connection", return_value=mock_connection
    ) as mock_serial:
        await main_fn

    assert main.__name__ == main_fn.__name__
    mock_asyncio_run.assert_called_once()
    mock_serial.assert_called_with("/dev/ttyUSB0", 115200)
    mock_connection.__aenter__.assert_awaited_once()
    mock_connection.get.assert_awaited_once_with("ecomax")
    mock_device.get.assert_has_calls([call("sensors"), call("parameters")])
    captured = capsys.readouterr()
    assert captured.out == "one\ntwo\n"
