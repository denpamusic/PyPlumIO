"""Contains tests for Connection classes."""

import asyncio
from asyncio import StreamReader, StreamWriter
import logging
from unittest.mock import patch

import pytest
from serial import SerialException
import serial_asyncio

from pyplumio.connection import SerialConnection, TcpConnection
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


@patch("pyplumio.connection.FrameWriter")
@patch("pyplumio.connection.FrameReader")
async def test_tcp_connect(
    mock_reader,
    mock_writer,
    mock_protocol,
    open_tcp_connection,
    tcp_connection: TcpConnection,
    stream_reader: StreamReader,
    stream_writer: StreamWriter,
) -> None:
    """Test tcp connection logic."""
    await tcp_connection.connect()
    assert isinstance(tcp_connection.protocol, Protocol)
    open_tcp_connection.assert_called_once_with(
        host="localhost", port=8899, test="test"
    )
    mock_reader.assert_called_with(stream_reader)
    mock_writer.assert_called_with(stream_writer)
    assert mock_reader.return_value in mock_protocol.call_args.args
    assert mock_writer.return_value in mock_protocol.call_args.args
    assert "connection_lost_callback" in mock_protocol.call_args.kwargs
    with patch("pyplumio.connection.Connection._reconnect") as mock_reconnect:
        mock_protocol.call_args.kwargs["connection_lost_callback"]()
        mock_reconnect.assert_called_once()


async def test_serial_connect(
    mock_protocol,
    open_serial_connection,
    serial_connection: SerialConnection,
) -> None:
    """Test serial connection logic."""
    await serial_connection.connect()
    open_serial_connection.assert_called_once_with(
        url="/dev/ttyUSB0",
        baudrate=115200,
        bytesize=serial_asyncio.serial.EIGHTBITS,
        parity=serial_asyncio.serial.PARITY_NONE,
        stopbits=serial_asyncio.serial.STOPBITS_ONE,
        test="test",
    )


async def test_reconnect(
    mock_protocol,
    open_tcp_connection,
    tcp_connection: TcpConnection,
    bypass_asyncio_sleep,
    caplog,
) -> None:
    """Test reconnect logic."""
    with patch(
        "pyplumio.connection.Connection._connect",
        side_effect=(ConnectionError, SerialException, asyncio.TimeoutError, None),
    ) as mock_connect:
        await tcp_connection.connect()

    with caplog.at_level(logging.ERROR):
        assert "Connection error" in caplog.text

    assert mock_connect.call_count == 4


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
    instance.wait_for_device.return_value = None
    await tcp_connection.connect()
    await tcp_connection.wait_for_device("test")
    instance.wait_for_device.assert_called_once()


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
    assert "host = localhost" in tcp_repr
    assert "port = 8899" in tcp_repr
    serial_repr = repr(serial_connection)
    assert "SerialConnection" in serial_repr
    assert "device = /dev/ttyUSB0" in serial_repr
    assert "baudrate = 115200" in serial_repr
