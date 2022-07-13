"""Contains tests for connection."""

import logging
from unittest.mock import patch

import pytest
from serial import SerialException
import serial_asyncio

from pyplumio.connection import SerialConnection, TcpConnection
from pyplumio.exceptions import ConnectionFailedError
from pyplumio.protocol import Protocol


@pytest.fixture(name="tcp_connection")
def fixture_tcp_connection() -> TcpConnection:
    """Return tcp connection object."""
    return TcpConnection(host="localhost", port=8899, test="test")


@pytest.fixture(name="serial_connection")
def fixture_serial_connection() -> SerialConnection:
    """Return serial connection object."""
    return SerialConnection(device="/dev/ttyUSB0", test="test")


@pytest.fixture(name="mock_protocol")
def fixture_mock_protocol():
    """Return mock Protocol object."""
    with patch("pyplumio.connection.Protocol", autospec=True) as mock_protocol:
        yield mock_protocol


@patch("pyplumio.connection.Connection._connection_lost_callback")
async def test_tcp_connect(
    mock_connection_lost_callback,
    mock_protocol,
    open_tcp_connection,
) -> None:
    """Test tcp connection logic."""
    tcp_connection = TcpConnection(
        host="localhost", port=8899, test="test", reconnect_on_failure=False
    )
    await tcp_connection.connect()
    assert isinstance(tcp_connection.protocol, Protocol)
    open_tcp_connection.assert_called_once_with(
        host="localhost", port=8899, test="test"
    )
    mock_protocol.assert_called_once_with(mock_connection_lost_callback, None, None)
    await tcp_connection.close()

    # Raise custom exception on connection failure.
    open_tcp_connection.side_effect = OSError
    with pytest.raises(ConnectionFailedError):
        await tcp_connection.connect()


async def test_serial_connect(
    mock_protocol,
    open_serial_connection,
) -> None:
    """Test serial connection logic."""
    serial_connection = SerialConnection(
        device="/dev/ttyUSB0", test="test", reconnect_on_failure=False
    )
    await serial_connection.connect()
    open_serial_connection.assert_called_once_with(
        url="/dev/ttyUSB0",
        baudrate=115200,
        bytesize=serial_asyncio.serial.EIGHTBITS,
        parity=serial_asyncio.serial.PARITY_NONE,
        stopbits=serial_asyncio.serial.STOPBITS_ONE,
        test="test",
    )

    # Raise custom exception on connection failure.
    open_serial_connection.side_effect = SerialException
    with pytest.raises(ConnectionFailedError):
        await serial_connection.connect()


async def test_reconnect(
    mock_protocol,
    open_tcp_connection,
    tcp_connection: TcpConnection,
    bypass_asyncio_sleep,
    caplog,
) -> None:
    """Test reconnect logic."""
    with caplog.at_level(logging.ERROR), patch(
        "pyplumio.connection.Connection._connect",
        side_effect=(ConnectionFailedError, None),
    ) as mock_connect:
        await tcp_connection.connect()

    assert "ConnectionError" in caplog.text
    assert mock_connect.call_count == 2


async def test_connection_lost_callback(
    mock_protocol,
    open_tcp_connection,
    tcp_connection: TcpConnection,
) -> None:
    """Test that connection lost callback calls reconnect."""
    await tcp_connection.connect()
    with patch("pyplumio.connection.Connection._reconnect") as mock_reconnect:
        connection_lost_callback = mock_protocol.call_args.args[0]
        await connection_lost_callback()
        mock_reconnect.assert_called_once()


@patch("pyplumio.connection.Connection._connect")
@patch("pyplumio.connection.Connection._reconnect")
async def test_reconnect_logic_selection(
    mock_reconnect,
    mock_connect,
) -> None:
    """Test reconnect logic selection."""
    connection = TcpConnection(host="localhost", port=8899, reconnect_on_failure=False)
    await connection.connect()
    mock_reconnect.assert_not_called()
    mock_connect.assert_called_once()


@patch("pyplumio.connection.Connection.close")
@patch("pyplumio.connection.Connection.connect")
async def test_context_manager(
    mock_connect,
    mock_close,
) -> None:
    """Test context manager integration."""
    async with TcpConnection(host="localhost", port=8899):
        pass

    mock_connect.assert_called_once()
    mock_close.assert_called_once()


async def test_getattr(
    mock_protocol,
    open_tcp_connection,
    tcp_connection: TcpConnection,
) -> None:
    """Test that getattr is getting proxied to the protocol."""
    instance = mock_protocol.return_value
    instance.get_device.return_value = None
    await tcp_connection.connect()
    await tcp_connection.get_device("test")
    instance.get_device.assert_called_once()


async def test_close(
    mock_protocol,
    open_tcp_connection,
    tcp_connection: TcpConnection,
) -> None:
    """Test connection close."""
    await tcp_connection.connect()
    await tcp_connection.close()
    instance = mock_protocol.return_value
    instance.shutdown.assert_called_once()


async def test_repr(
    tcp_connection: TcpConnection,
    serial_connection: SerialConnection,
) -> None:
    """Test serializable representation."""
    tcp_repr = repr(tcp_connection)
    assert "TcpConnection" in tcp_repr
    assert "host=localhost" in tcp_repr
    assert "port=8899" in tcp_repr
    serial_repr = repr(serial_connection)
    assert "SerialConnection" in serial_repr
    assert "device=/dev/ttyUSB0" in serial_repr
    assert "baudrate=115200" in serial_repr
