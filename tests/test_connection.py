"""Contains tests for the connection classes."""

from asyncio import StreamReader, StreamWriter
from importlib import reload
import logging
import sys
from typing import Final
from unittest.mock import AsyncMock, patch

import pytest
from serial import EIGHTBITS, PARITY_NONE, STOPBITS_ONE, SerialException

import pyplumio.connection
from pyplumio.exceptions import ConnectionFailedError
from pyplumio.protocol import Protocol

HOST: Final = "localhost"
PORT: Final = 8899
DEVICE: Final = "/dev/ttyUSB0"


@pytest.fixture(name="use_fast", params=(True, False))
def fixture_use_fast(request, monkeypatch, caplog):
    """Try with and without serial-asyncio-fast package."""
    if not request.param:
        monkeypatch.setitem(sys.modules, "serial_asyncio_fast", None)

    with caplog.at_level(logging.INFO):
        reload(pyplumio.connection)

    message = "Using pyserial-asyncio-fast in place of pyserial-asyncio"
    assert (message in caplog.text) if request.param else (message not in caplog.text)
    return request.param


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
    use_fast, stream_reader: StreamReader, stream_writer: StreamWriter
):
    """Bypass opening serial_asyncio connection."""
    module = "serial_asyncio_fast" if use_fast else "serial_asyncio"
    with patch(
        f"{module}.open_serial_connection",
        return_value=(stream_reader, stream_writer),
    ) as mock_connection:
        yield mock_connection


@pytest.fixture(name="mock_protocol")
def fixture_mock_protocol():
    """Return a mock protocol object."""
    return AsyncMock(spec=Protocol)


@pytest.fixture(name="tcp_connection")
def fixture_tcp_connection(mock_protocol) -> pyplumio.connection.TcpConnection:
    """Return at TCP connection object."""
    return pyplumio.connection.TcpConnection(
        host=HOST, port=PORT, timeout=10, protocol=mock_protocol
    )


@pytest.fixture(name="serial_connection")
def fixture_serial_connection(mock_protocol) -> pyplumio.connection.SerialConnection:
    """Return a serial connection object."""
    return pyplumio.connection.SerialConnection(
        device="/dev/ttyUSB0", timeout=10, protocol=mock_protocol
    )


async def test_tcp_connect(mock_protocol, asyncio_open_connection) -> None:
    """Test TCP connection logic."""
    with patch("pyplumio.connection.Connection._reconnect") as mock_reconnect:
        tcp_connection = pyplumio.connection.TcpConnection(
            host=HOST,
            port=PORT,
            timeout=10,
            protocol=mock_protocol,
            reconnect_on_failure=True,
        )

        assert tcp_connection.protocol == mock_protocol
        mock_protocol.on_connection_lost.add.assert_called_once_with(mock_reconnect)

    await tcp_connection.connect()
    asyncio_open_connection.assert_called_once_with(host=HOST, port=PORT, timeout=10)
    await tcp_connection.close()

    # Raise custom exception on connection failure.
    tcp_connection = pyplumio.connection.TcpConnection(
        host=HOST,
        port=PORT,
        timeout=10,
        protocol=mock_protocol,
        reconnect_on_failure=False,
    )

    asyncio_open_connection.side_effect = OSError
    with pytest.raises(ConnectionFailedError):
        await tcp_connection.connect()


async def test_serial_connect(
    mock_protocol, serial_asyncio_open_serial_connection
) -> None:
    """Test a serial connection logic."""
    serial_connection = pyplumio.connection.SerialConnection(
        device=DEVICE, timeout=10, reconnect_on_failure=False, protocol=mock_protocol
    )
    await serial_connection.connect()
    serial_asyncio_open_serial_connection.assert_called_once_with(
        url=DEVICE,
        baudrate=115200,
        bytesize=EIGHTBITS,
        parity=PARITY_NONE,
        stopbits=STOPBITS_ONE,
        timeout=10,
    )

    # Raise custom exception on connection failure.
    serial_asyncio_open_serial_connection.side_effect = SerialException
    with pytest.raises(ConnectionFailedError):
        await serial_connection.connect()


@pytest.mark.usefixtures("asyncio_open_connection")
async def test_reconnect(
    tcp_connection: pyplumio.connection.TcpConnection, caplog
) -> None:
    """Test a reconnect logic."""
    with caplog.at_level(logging.ERROR), patch(
        "pyplumio.connection.Connection._connect",
        side_effect=(ConnectionFailedError, None),
    ) as mock_connect:
        await tcp_connection.connect()
        await tcp_connection.wait_until_done()

    assert "Can't connect to the device" in caplog.text
    assert mock_connect.call_count == 2


@pytest.mark.usefixtures("asyncio_open_connection")
async def test_connection_lost(
    mock_protocol, tcp_connection: pyplumio.connection.TcpConnection
) -> None:
    """Test that connection lost callback calls reconnect."""
    await tcp_connection.connect()
    on_connection_lost = mock_protocol.on_connection_lost.add.call_args.args[0]
    with patch("pyplumio.connection.Connection._connect") as mock_connect:
        await on_connection_lost()
        mock_connect.assert_called_once()


async def test_reconnect_logic_selection() -> None:
    """Test reconnect logic selection."""
    connection = pyplumio.connection.TcpConnection(
        host=HOST, port=PORT, reconnect_on_failure=False
    )

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
    async with pyplumio.connection.TcpConnection(host=HOST, port=PORT):
        pass

    mock_connect.assert_called_once()
    mock_close.assert_called_once()


@pytest.mark.usefixtures("asyncio_open_connection")
async def test_getattr(
    mock_protocol, tcp_connection: pyplumio.connection.TcpConnection
) -> None:
    """Test that getattr is getting proxied to the protocol."""
    mock_protocol.get_device = AsyncMock()
    await tcp_connection.connect()
    await tcp_connection.get_device("test")
    mock_protocol.get_device.assert_called_once()


@pytest.mark.usefixtures("asyncio_open_connection")
async def test_close(
    mock_protocol, tcp_connection: pyplumio.connection.TcpConnection
) -> None:
    """Test connection close."""
    await tcp_connection.connect()
    await tcp_connection.close()
    mock_protocol.shutdown.assert_called_once()


async def test_repr(
    tcp_connection: pyplumio.connection.TcpConnection,
    serial_connection: pyplumio.connection.SerialConnection,
) -> None:
    """Test serializable representation."""
    assert (
        repr(tcp_connection)
        == f"TcpConnection(host={HOST}, port={PORT}, kwargs={{'timeout': 10}})"
    )
    assert repr(serial_connection) == (
        f"SerialConnection(device={DEVICE}, baudrate=115200, "
        f"kwargs={{'timeout': 10}})"
    )
