"""Contains tests for the connection classes."""

from __future__ import annotations

from asyncio import StreamReader, StreamWriter
import logging
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
from serialx import Parity, StopBits

from pyplumio.connection import RECONNECT_AFTER_SECONDS, Connection, SerialConnection
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.exceptions import ConnectionFailedError
from pyplumio.protocol import AsyncProtocol, DummyProtocol, Protocol


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


@pytest.fixture(name="serialx_open_serial_connection")
def serialx_open_serial_connection(
    stream_reader: StreamReader, stream_writer: StreamWriter
):
    """Bypass opening serial_asyncio connection."""
    with patch(
        "serialx.open_serial_connection", return_value=(stream_reader, stream_writer)
    ) as mock_connection:
        yield mock_connection


@pytest.fixture(name="mock_protocol")
def fixture_mock_protocol():
    """Return a mock protocol object."""
    return AsyncMock(spec=Protocol, autospec=True)


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
        mock_protocol.shutdown = AsyncMock()
        connection = DummyConnection(protocol=mock_protocol)
        assert connection.protocol is mock_protocol
        await connection.connect()
        mock_open_connection.assert_awaited_once()
        await connection.close()
        mock_protocol.shutdown.assert_awaited_once()

    @pytest.mark.parametrize("reconnect_on_failure", [True, False])
    @patch.object(
        DummyConnection,
        "_open_connection",
        side_effect=(OSError, (AsyncMock(), AsyncMock), None),
    )
    @patch("pyplumio.protocol.AsyncProtocol.connection_established")
    async def test_reconnect(
        self,
        mock_connection_established,
        mock_open_connection,
        caplog,
        reconnect_on_failure: bool,
    ) -> None:
        """Test reconnect logic."""
        connection = DummyConnection(reconnect_on_failure=reconnect_on_failure)
        if reconnect_on_failure:
            with caplog.at_level(logging.ERROR):
                await connection.connect()
                assert "Unable to connect to the device." in caplog.text
                assert (
                    f"automatically every {RECONNECT_AFTER_SECONDS} seconds"
                    in caplog.text
                )

            with caplog.at_level(logging.INFO):
                await connection.connect()
                assert "Connection to device restored after 1 retries" in caplog.text
                mock_connection_established.assert_called_once()

            assert mock_open_connection.await_count == 2

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

    async def test_device_context_manager(self, ecomax: EcoMAX) -> None:
        """Test device context manager."""
        mock_protocol = AsyncMock(spec=AsyncProtocol)
        mock_protocol.get = AsyncMock(return_value=ecomax)
        connection = DummyConnection(protocol=mock_protocol)

        async with connection.device("ecomax") as device:
            assert isinstance(device, EcoMAX)

        mock_protocol.get.assert_awaited_once_with("ecomax", timeout=None)

    async def test_device_context_manager_with_unsupported_protocol(self) -> None:
        """Test device context with unsupported protocol."""
        mock_protocol = AsyncMock(spec=DummyProtocol)
        connection = DummyConnection(protocol=mock_protocol)
        with pytest.raises(NotImplementedError):
            async with connection.device("ecomax"):
                pytest.fail("Entered context manager without AsyncProtocol")

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


class TestSerialConnection:
    """Contains tests for SerialConnection class."""

    @pytest.mark.parametrize(
        ("url", "options", "expected_options"),
        (
            (
                "/dev/ttyUSB0",
                {},
                {
                    "baudrate": 115200,
                    "byte_size": 8,
                    "parity": Parity.NONE,
                    "stopbits": StopBits.ONE,
                },
            ),
            (
                "/dev/ttyAMA0",
                {"timeout": 15},
                {
                    "baudrate": 115200,
                    "byte_size": 8,
                    "parity": Parity.NONE,
                    "stopbits": StopBits.ONE,
                    "timeout": 15,
                },
            ),
            ("socket://localhost:8899", {}, {}),
            ("socket://localhost:8900", {"timeout": 10}, {"timeout": 10}),
        ),
    )
    async def test_connect(
        self,
        url: str,
        options: dict[str, Any],
        expected_options: dict[str, Any],
        serialx_open_serial_connection,
        mock_protocol,
    ) -> None:
        """Test serial connect."""
        serial_connection = SerialConnection(url=url, protocol=mock_protocol, **options)
        await serial_connection.connect()
        serialx_open_serial_connection.assert_called_once_with(url, **expected_options)

    def test_repr(self) -> None:
        """Test serializable representation."""
        serial_connection = SerialConnection(url="/dev/ttyUSB0", timeout=10)
        assert repr(serial_connection) == (
            "SerialConnection(url=/dev/ttyUSB0, options={'baudrate': 115200, "
            "'byte_size': 8, 'parity': <Parity.NONE: 'N'>, 'stopbits': "
            "<StopBits.ONE: 1.0>, 'timeout': 10})"
        )
