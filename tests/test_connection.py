"""Contains tests for the connection classes."""

from __future__ import annotations

from asyncio import StreamReader, StreamWriter
from importlib import reload
import logging
import sys
from typing import Final
from unittest.mock import AsyncMock, Mock, patch

import pytest
from serial import EIGHTBITS, PARITY_NONE, STOPBITS_ONE

from pyplumio.connection import Connection, SerialConnection, TcpConnection
from pyplumio.exceptions import ConnectionFailedError
from pyplumio.protocol import Protocol


@pytest.fixture(name="use_fast", params=(True, False))
def fixture_use_fast(request, monkeypatch, caplog):
    """Try with and without serial-asyncio-fast package."""
    import pyplumio.connection

    if not request.param:
        monkeypatch.setitem(sys.modules, "serial_asyncio_fast", None)

    with caplog.at_level(logging.INFO):
        reload(pyplumio.connection)

    message = "Using pyserial-asyncio-fast in place of pyserial-asyncio"
    if request.param:
        assert message in caplog.text
    else:
        assert message not in caplog.text

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
    return AsyncMock(spec=Protocol, autospec=True)


@pytest.fixture(name="tcp_connection")
def fixture_tcp_connection(mock_protocol) -> TcpConnection:
    """Return at TCP connection object."""
    return TcpConnection(host=HOST, port=PORT, timeout=10, protocol=mock_protocol)


@pytest.fixture(name="serial_connection")
def fixture_serial_connection(mock_protocol) -> SerialConnection:
    """Return a serial connection object."""
    return SerialConnection(device="/dev/ttyUSB0", timeout=10, protocol=mock_protocol)


class DummyConnection(Connection):
    """Represents a dummy connection for tests."""

    async def _open_connection(self):
        """Open the connection."""


class TestConnection:
    """Contains test for Connection class."""

    @patch.object(
        DummyConnection, "_open_connection", return_value=("reader", "writer")
    )
    async def test_connect(self, mock_open_connection, mock_protocol) -> None:
        """Test a connection."""
        connection = DummyConnection(protocol=mock_protocol)
        assert connection.protocol is mock_protocol
        await connection.connect()
        mock_open_connection.assert_awaited_once()
        await connection.close()
        mock_protocol.shutdown.assert_called_once()

    @pytest.mark.parametrize(
        ("reconnect_on_failure", "expected_log"),
        [
            (True, "Can't connect to the device"),
            (False, None),
        ],
    )
    @patch.object(DummyConnection, "_open_connection", side_effect=(OSError, None))
    async def test_reconnect(
        self,
        mock_open_connection,
        caplog,
        reconnect_on_failure: bool,
        expected_log: str | None,
    ) -> None:
        """Test reconnect logic."""
        connection = DummyConnection(reconnect_on_failure=reconnect_on_failure)
        if reconnect_on_failure:
            with caplog.at_level(logging.ERROR):
                await connection.connect()

            assert expected_log in caplog.text
        else:
            with pytest.raises(ConnectionFailedError):
                await connection.connect()

        mock_open_connection.assert_awaited_once()

    @patch.object(DummyConnection, "close")
    @patch.object(DummyConnection, "connect")
    async def test_context_manager(self, mock_connect, mock_close) -> None:
        """Test context manager."""
        async with DummyConnection():
            ...

        mock_connect.assert_called_once()
        mock_close.assert_called_once()

    @patch.object(DummyConnection, "_connect")
    async def test_connection_lost(self, mock_connect, mock_protocol) -> None:
        """Test that connection lost callback calls reconnect."""
        connection = DummyConnection(protocol=mock_protocol)
        await connection.connect()
        on_connection_lost = mock_protocol.on_connection_lost.add.call_args.args[0]
        await on_connection_lost()
        assert mock_connect.call_count == 2

    async def test_getattr(self, mock_protocol) -> None:
        """Test that getattr is getting proxied to the protocol."""
        connection = DummyConnection(protocol=mock_protocol)
        mock_protocol.some_attr = "value"
        assert connection.some_attr == "value"
        mock_protocol.some_method = Mock(return_value="called")
        assert connection.some_method() == "called"


HOST: Final = "localhost"
PORT: Final = 8899


class TestTcpConnection:
    """Contains tests for TcpConnection class."""

    async def test_connection(
        self, tcp_connection: TcpConnection, asyncio_open_connection
    ) -> None:
        """Test TCP connection."""
        await tcp_connection.connect()
        asyncio_open_connection.assert_awaited_once_with(
            host=HOST, port=PORT, timeout=10
        )

    async def test_repr(self, tcp_connection: TcpConnection) -> None:
        """Test serializable representation."""
        assert (
            repr(tcp_connection)
            == f"TcpConnection(host={HOST}, port={PORT}, kwargs={{'timeout': 10}})"
        )


DEVICE: Final = "/dev/ttyUSB0"


class TestSerialConnection:
    """Contains tests for SerialConnection class."""

    async def test_connect(
        self, serial_connection: SerialConnection, serial_asyncio_open_serial_connection
    ) -> None:
        """Test serial connect."""
        await serial_connection.connect()
        serial_asyncio_open_serial_connection.assert_called_once_with(
            url=DEVICE,
            baudrate=115200,
            bytesize=EIGHTBITS,
            parity=PARITY_NONE,
            stopbits=STOPBITS_ONE,
            timeout=10,
        )

    async def test_repr(self, serial_connection: SerialConnection) -> None:
        """Test serializable representation."""
        assert repr(serial_connection) == (
            "SerialConnection("
            f"device={DEVICE}, baudrate=115200, kwargs={{'timeout': 10}})"
        )
