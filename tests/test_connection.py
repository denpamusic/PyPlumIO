"""Contains tests for the connection classes."""

from asyncio import StreamReader, StreamWriter
import logging
from typing import Final
from unittest.mock import AsyncMock, Mock, patch

import pytest
from serial import SerialException
import serial_asyncio

from pyplumio.connection import SerialConnection, TcpConnection
from pyplumio.exceptions import ConnectionFailedError
from pyplumio.protocol import Protocol

HOST: Final = "localhost"
PORT: Final = 8899
DEVICE: Final = "/dev/ttyUSB0"


@pytest.fixture(name="stream_writer")
def fixture_stream_writer():
    """Return a mock of asyncio stream writer."""
    with patch("asyncio.StreamWriter", autospec=True) as mock_stream_writer:
        yield mock_stream_writer


@pytest.fixture(name="stream_reader")
def fixture_stream_reader():
    """Return a mock of asyncio stream reader."""
    with patch("asyncio.StreamReader", autospec=True) as mock_stream_reader:
        yield mock_stream_reader


@pytest.fixture(name="asyncio_open_connection")
def fixture_asyncio_open_connection(
    stream_reader: StreamReader, stream_writer: StreamWriter
):
    """Bypass opening asyncio connection."""
    with patch(
        "asyncio.open_connection", return_value=(stream_reader, stream_writer)
    ) as mock_connection:
        yield mock_connection


@pytest.fixture(name="serial_asyncio_open_serial_connection")
def fixture_serial_asyncio_open_serial_connection(
    stream_reader: StreamReader, stream_writer: StreamWriter
):
    """Bypass opening serial_asyncio connection."""
    with patch(
        "serial_asyncio.open_serial_connection",
        return_value=(stream_reader, stream_writer),
    ) as mock_connection:
        yield mock_connection


@pytest.fixture(name="mock_protocol")
def fixture_mock_protocol():
    """Return a mock protocol object."""
    return Mock(return_value=AsyncMock(spec=Protocol))


@pytest.fixture(name="tcp_connection")
def fixture_tcp_connection(mock_protocol) -> TcpConnection:
    """Return at TCP connection object."""
    return TcpConnection(host=HOST, port=PORT, test="test", protocol=mock_protocol)


@pytest.fixture(name="serial_connection")
def fixture_serial_connection(mock_protocol) -> SerialConnection:
    """Return a serial connection object."""
    return SerialConnection(device="/dev/ttyUSB0", test="test", protocol=mock_protocol)


async def test_tcp_connect(mock_protocol, asyncio_open_connection) -> None:
    """Test TCP connection logic."""

    with patch(
        "pyplumio.connection.Connection._connection_lost"
    ) as mock_connection_lost:
        tcp_connection = TcpConnection(
            host=HOST,
            port=PORT,
            test="test",
            reconnect_on_failure=False,
            protocol=mock_protocol,
        )

        assert tcp_connection.protocol == mock_protocol.return_value
        mock_protocol.assert_called_once_with(mock_connection_lost, None, None)

    await tcp_connection.connect()
    asyncio_open_connection.assert_called_once_with(host=HOST, port=PORT, test="test")
    await tcp_connection.close()

    # Raise custom exception on connection failure.
    asyncio_open_connection.side_effect = OSError
    with pytest.raises(ConnectionFailedError):
        await tcp_connection.connect()


async def test_serial_connect(
    mock_protocol, serial_asyncio_open_serial_connection
) -> None:
    """Test a serial connection logic."""
    serial_connection = SerialConnection(
        device=DEVICE, test="test", reconnect_on_failure=False, protocol=mock_protocol
    )
    await serial_connection.connect()
    serial_asyncio_open_serial_connection.assert_called_once_with(
        url=DEVICE,
        baudrate=115200,
        bytesize=serial_asyncio.serial.EIGHTBITS,
        parity=serial_asyncio.serial.PARITY_NONE,
        stopbits=serial_asyncio.serial.STOPBITS_ONE,
        test="test",
    )

    # Raise custom exception on connection failure.
    serial_asyncio_open_serial_connection.side_effect = SerialException
    with pytest.raises(ConnectionFailedError):
        await serial_connection.connect()


@pytest.mark.usefixtures("asyncio_open_connection")
async def test_reconnect(tcp_connection: TcpConnection, caplog) -> None:
    """Test a reconnect logic."""
    with caplog.at_level(logging.ERROR), patch(
        "pyplumio.connection.Connection._connect",
        side_effect=(ConnectionFailedError, None),
    ) as mock_connect:
        await tcp_connection.connect()

    assert "Can't connect to the device" in caplog.text
    assert mock_connect.call_count == 2


@pytest.mark.usefixtures("asyncio_open_connection")
async def test_connection_lost(mock_protocol, tcp_connection: TcpConnection) -> None:
    """Test that connection lost callback calls reconnect."""
    await tcp_connection.connect()
    connection_lost_callback = mock_protocol.call_args.args[0]
    with patch("pyplumio.connection.Connection._reconnect") as mock_reconnect:
        await connection_lost_callback()
        mock_reconnect.assert_called_once()


async def test_reconnect_logic_selection() -> None:
    """Test reconnect logic selection."""
    connection = TcpConnection(host=HOST, port=PORT, reconnect_on_failure=False)

    with patch("pyplumio.connection.Connection._connect") as mock_connect, patch(
        "pyplumio.connection.Connection._reconnect"
    ) as mock_reconnect:
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
    async with TcpConnection(host=HOST, port=PORT):
        pass

    mock_connect.assert_called_once()
    mock_close.assert_called_once()


@pytest.mark.usefixtures("asyncio_open_connection")
async def test_getattr(mock_protocol, tcp_connection: TcpConnection) -> None:
    """Test that getattr is getting proxied to the protocol."""
    mock_protocol.return_value.get_device = AsyncMock()
    await tcp_connection.connect()
    await tcp_connection.get_device("test")
    mock_protocol.return_value.get_device.assert_called_once()


@pytest.mark.usefixtures("asyncio_open_connection")
async def test_close(mock_protocol, tcp_connection: TcpConnection) -> None:
    """Test connection close."""
    await tcp_connection.connect()
    await tcp_connection.close()
    instance = mock_protocol.return_value
    instance.shutdown.assert_called_once()


async def test_repr(
    tcp_connection: TcpConnection, serial_connection: SerialConnection
) -> None:
    """Test serializable representation."""
    assert (
        repr(tcp_connection)
        == f"TcpConnection(host={HOST}, port={PORT}, kwargs={{'test': 'test'}})"
    )
    assert (
        repr(serial_connection)
        == f"SerialConnection(device={DEVICE}, baudrate=115200, kwargs={{'test': 'test'}})"
    )
