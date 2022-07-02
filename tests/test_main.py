"""Contains tests for main."""

from unittest.mock import AsyncMock, call, patch


@patch("asyncio.run")
async def test_main(mock_asyncio_run, capsys) -> None:
    """Test main."""
    mock_device = AsyncMock()
    mock_device.get_value.side_effect = ("one", "two")
    mock_connection = AsyncMock()
    mock_connection.__aenter__.return_value = mock_connection
    mock_connection.wait_for_device.return_value = mock_device

    import pyplumio.__main__ as entry

    with patch(
        "pyplumio.open_serial_connection", return_value=mock_connection
    ) as mock_open_serial_connection:
        await entry.main()

    mock_open_serial_connection.assert_called_with("/dev/ttyUSB0", 115200)
    mock_connection.__aenter__.assert_awaited_once()
    mock_connection.wait_for_device.assert_awaited_once_with("ecomax")
    calls = [call("sensors"), call("parameters")]
    mock_device.get_value.assert_has_calls(calls)
    captured = capsys.readouterr()
    assert captured.out == "one\ntwo\n"
