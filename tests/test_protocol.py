"""Contains tests for the protocol classes."""

import asyncio
from datetime import datetime
import logging
from unittest.mock import AsyncMock, Mock, call, patch

import pytest

from pyplumio.const import ATTR_CONNECTED, ATTR_SETUP, DeviceType
from pyplumio.devices import PhysicalDevice
from pyplumio.exceptions import ProtocolError
from pyplumio.frames import Request, Response
from pyplumio.protocol import NEVER, AsyncProtocol, DummyProtocol, Statistics
from pyplumio.stream import FrameReader, FrameWriter


@pytest.fixture(name="skip_asyncio_create_task", autouse=True)
def fixture_skip_asyncio_create_task():
    """Bypass asyncio create task."""
    with patch("asyncio.create_task"):
        yield


class TestDummyProtocol:
    """Contains tests for DummyProtocol class."""

    @patch("pyplumio.protocol.FrameReader", autospec=True)
    @patch("pyplumio.protocol.FrameWriter", autospec=True)
    def test_connection_established(self, mock_frame_writer, mock_frame_reader) -> None:
        """Test establishing the connection."""
        protocol = DummyProtocol()
        mock_reader = AsyncMock(spec=asyncio.StreamReader, autospec=True)
        mock_writer = AsyncMock(spec=asyncio.StreamWriter, autospec=True)
        assert not protocol.connected.is_set()
        protocol.connection_established(reader=mock_reader, writer=mock_writer)
        assert protocol.connected.is_set()
        mock_frame_reader.assert_called_once_with(mock_reader)
        mock_frame_writer.assert_called_once_with(mock_writer)
        assert protocol.reader is mock_frame_reader.return_value
        assert protocol.writer is mock_frame_writer.return_value

    @patch("asyncio.Event.is_set", return_value=True)
    @patch("asyncio.Event.clear")
    async def test_connection_lost(self, mock_clear, mock_is_set) -> None:
        """Test connection lost."""
        protocol = DummyProtocol()
        mock_connection_lost_callback = AsyncMock()
        protocol.on_connection_lost.add(mock_connection_lost_callback)
        mock_writer = AsyncMock(spec=FrameWriter, autospec=True)
        protocol.writer = mock_writer
        await protocol.connection_lost()
        mock_is_set.assert_called_once()
        mock_clear.assert_called_once()
        mock_connection_lost_callback.assert_awaited_once()
        mock_writer.close.assert_awaited_once()

    @patch("pyplumio.protocol.FrameWriter.close")
    async def test_shutdown(self, mock_close) -> None:
        """Test shutting down."""
        protocol = DummyProtocol()
        protocol.connected.set()
        mock_stream_writer = AsyncMock(spec=asyncio.StreamWriter, autospec=True)
        protocol.writer = FrameWriter(mock_stream_writer)
        await protocol.shutdown()
        mock_close.assert_awaited_once()
        assert not protocol.connected.is_set()
        assert protocol.writer is None


request = Request()
response = Response(sender=DeviceType.ECOMAX)


class TestAsyncProtocol:
    """Contains tests for AsyncProtocol class."""

    @patch("pyplumio.protocol.FrameReader", autospec=True)
    @patch("pyplumio.protocol.FrameWriter", autospec=True)
    @patch("pyplumio.protocol.AsyncProtocol.frame_handler", new_callable=Mock)
    @patch("pyplumio.protocol.Statistics.reset_transfer_statistics")
    @patch("pyplumio.protocol.StartMasterRequest")
    @patch("asyncio.Queue.put_nowait")
    @patch("asyncio.create_task")
    @pytest.mark.usefixtures("frozen_time")
    async def test_connection_established(
        self,
        mock_create_task,
        mock_put_nowait,
        mock_start_master_request,
        mock_reset_transfer_statistics,
        mock_frame_handler,
        mock_frame_writer,
        mock_frame_reader,
    ) -> None:
        """Test establishing the connection."""
        protocol = AsyncProtocol()
        mock_reader = AsyncMock(spec=asyncio.StreamReader, autospec=True)
        mock_writer = AsyncMock(spec=asyncio.StreamWriter, autospec=True)
        mock_physical_device = Mock(spec=PhysicalDevice)
        await protocol.dispatch("physical_device", mock_physical_device)
        assert not protocol.connected.is_set()
        assert protocol.statistics.connected_since == NEVER
        protocol.connection_established(reader=mock_reader, writer=mock_writer)
        assert protocol.connected.is_set()
        assert protocol.network_info.server_status is True

        # Test frame handler task was created.
        mock_frame_handler.assert_called_once_with(
            reader=mock_frame_reader.return_value, writer=mock_frame_writer.return_value
        )
        mock_create_task.assert_called_once_with(
            mock_frame_handler.return_value, name="frame_handler_task"
        )

        # Test devices were notified.
        mock_physical_device.dispatch_nowait.assert_called_once_with(
            ATTR_CONNECTED, True
        )
        mock_put_nowait.assert_called_once_with(mock_start_master_request.return_value)
        mock_start_master_request.assert_called_once_with(recipient=DeviceType.ECOMAX)

        # Test statistics was updated.
        mock_reset_transfer_statistics.assert_called_once()
        assert protocol.statistics.connected_since == datetime.now()

    @patch("asyncio.Event.is_set", return_value=True)
    @patch("asyncio.Event.clear")
    async def test_connection_lost(self, mock_clear, mock_is_set) -> None:
        """Test connection lost."""
        protocol = AsyncProtocol()
        mock_connection_lost_callback = AsyncMock()
        protocol.on_connection_lost.add(mock_connection_lost_callback)
        mock_physical_device = Mock(spec=PhysicalDevice)
        await protocol.dispatch("physical_device", mock_physical_device)
        mock_writer = AsyncMock(spec=FrameWriter, autospec=True)
        protocol.writer = mock_writer
        await protocol.connection_lost()
        mock_is_set.assert_called_once()
        mock_clear.assert_called_once()
        mock_writer.close.assert_awaited_once()
        mock_connection_lost_callback.assert_awaited_once()
        mock_physical_device.dispatch_nowait.assert_called_once_with(
            ATTR_CONNECTED, False
        )

    @patch("asyncio.Queue.empty", side_effect=(False, True))
    @patch("asyncio.Queue.get_nowait")
    @patch("asyncio.Queue.task_done")
    @patch("pyplumio.protocol.AsyncProtocol.cancel_tasks")
    async def test_shutdown(
        self, mock_cancel_tasks, mock_task_done, mock_get_nowait, mock_empty
    ) -> None:
        """Test connection shutdown."""
        protocol = AsyncProtocol()
        mock_physical_device = Mock(spec=PhysicalDevice)
        await protocol.dispatch("physical_device", mock_physical_device)
        protocol.connected.set()
        mock_writer = AsyncMock(spec=FrameWriter, autospec=True)
        protocol.writer = mock_writer
        await protocol.shutdown()
        mock_writer.close.assert_awaited_once()
        mock_physical_device.dispatch_nowait.assert_called_once_with(
            ATTR_CONNECTED, False
        )
        mock_physical_device.shutdown.assert_awaited_once()
        mock_cancel_tasks.assert_called_once()
        assert mock_empty.call_count == 2
        mock_get_nowait.assert_called_once()
        mock_task_done.assert_called_once()

    @pytest.fixture(name="statistics")
    @patch("asyncio.Queue.empty", side_effect=(False, True, True, True, True))
    @patch("asyncio.Queue.get", side_effect=(request,))
    @patch("asyncio.Queue.task_done")
    @patch("asyncio.create_task")
    @patch("pyplumio.protocol.AsyncProtocol.connection_lost", new_callable=Mock)
    @patch("pyplumio.protocol.FrameWriter.write")
    @patch(
        "pyplumio.protocol.FrameReader.read",
        side_effect=(response, response, ProtocolError, Exception, OSError),
    )
    @patch("pyplumio.devices.Device.dispatch_nowait")
    async def test_frame_handler(
        self,
        mock_dispatch_nowait,
        mock_read,
        mock_write,
        mock_connection_lost,
        mock_create_task,
        mock_task_done,
        mock_get,
        mock_empty,
        caplog,
    ) -> Statistics:
        """Test frame handler and return statistics."""
        protocol = AsyncProtocol()
        mock_reader = AsyncMock(spec=asyncio.StreamReader, autospec=True)
        mock_writer = AsyncMock(spec=asyncio.StreamWriter, autospec=True)
        protocol.connected.set()

        # Test initial statistics.
        statistics = protocol.statistics
        assert statistics.sent_bytes == 0
        assert statistics.sent_frames == 0
        assert statistics.received_bytes == 0
        assert statistics.received_frames == 0

        with caplog.at_level(logging.DEBUG):
            await protocol.frame_handler(
                reader=FrameReader(mock_reader), writer=FrameWriter(mock_writer)
            )

        # Test write.
        mock_task_done.assert_called_once()
        mock_get.assert_awaited_once()
        mock_write.assert_awaited_once_with(request)
        assert mock_empty.call_count == 5

        # Test read and device creation.
        assert mock_read.await_count == 5
        assert mock_dispatch_nowait.call_count == 2
        mock_dispatch_nowait.assert_has_calls(
            [call(ATTR_CONNECTED, True), call(ATTR_SETUP, True)]
        )

        # Test log messages.
        assert "Can't process received frame" in caplog.text
        assert "Unexpected exception" in caplog.text

        # Test connection lost.
        mock_connection_lost.assert_called_once()
        mock_create_task.assert_called_once_with(
            mock_connection_lost.return_value, name=None
        )

        return statistics

    @pytest.mark.usefixtures("frozen_time")
    async def test_statistics(self, statistics: Statistics) -> None:
        """Test protocol statistics."""
        assert statistics.sent_bytes == 10
        assert statistics.sent_frames == 1
        assert statistics.received_bytes == 20
        assert statistics.received_frames == 2
        assert statistics.failed_frames == 1
        statistics.reset_transfer_statistics()
        assert statistics.sent_bytes == 0
        assert statistics.sent_frames == 0
        assert statistics.received_bytes == 0
        assert statistics.sent_bytes == 0
        assert statistics.failed_frames == 0

        # Test device statistics.
        device_statistics = statistics.devices.pop()
        assert device_statistics.address == DeviceType.ECOMAX
        await device_statistics.update_last_seen()
        assert device_statistics.last_seen == datetime.now()
