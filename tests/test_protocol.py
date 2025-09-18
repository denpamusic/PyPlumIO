"""Contains tests for the protocol classes."""

import asyncio
from dataclasses import asdict
from datetime import datetime, timedelta
import logging
from typing import cast
from unittest.mock import AsyncMock, Mock, PropertyMock, call, patch

import pytest

from pyplumio.const import ATTR_CONNECTED, DeviceType, EncryptionType
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.exceptions import (
    FrameDataError,
    ProtocolError,
    ReadError,
    UnknownDeviceError,
    UnknownFrameError,
)
from pyplumio.frames import Request, Response
from pyplumio.frames.requests import (
    CheckDeviceRequest,
    ProgramVersionRequest,
    StartMasterRequest,
)
from pyplumio.protocol import AsyncProtocol, DummyProtocol, Queues, Statistics
from pyplumio.stream import FrameReader, FrameWriter
from pyplumio.structures.network_info import (
    EthernetParameters,
    NetworkInfo,
    WirelessParameters,
)
from pyplumio.structures.regulator_data import ATTR_REGDATA


@pytest.fixture(name="skip_asyncio_create_task")
def fixture_skip_asyncio_create_task():
    """Bypass asyncio create task."""
    with patch("asyncio.create_task"):
        yield


@pytest.fixture(name="async_protocol")
def fixture_async_protocol() -> AsyncProtocol:
    """Return an async protocol instance."""
    return AsyncProtocol(
        wireless_parameters=WirelessParameters(
            ssid="test_ssid",
            ip="2.2.2.2",
            encryption=EncryptionType.WPA2,
            netmask="255.255.255.255",
            gateway="2.2.2.1",
            signal_quality=50,
            status=True,
        ),
        ethernet_parameters=EthernetParameters(
            ip="1.1.1.2",
            netmask="255.255.255.255",
            gateway="1.1.1.1",
            status=True,
        ),
    )


async def test_dummy_protocol() -> None:
    """Test a dummy protocol."""
    mock_on_connection_lost = AsyncMock()
    dummy_protocol = DummyProtocol()
    dummy_protocol.on_connection_lost.add(mock_on_connection_lost)

    mock_reader = AsyncMock(spec=asyncio.StreamReader)
    mock_writer = AsyncMock(spec=asyncio.StreamWriter, new_callable=Mock)

    # Test establishing the connection.
    with (
        patch("pyplumio.protocol.FrameReader") as mock_frame_reader,
        patch("pyplumio.protocol.FrameWriter") as mock_frame_writer,
    ):
        dummy_protocol.connection_established(mock_reader, mock_writer)
        mock_frame_reader.assert_called_once_with(mock_reader)
        mock_frame_writer.assert_called_once_with(mock_writer)

    assert dummy_protocol.connected.is_set()

    # Test losing the connection.
    with patch(
        "pyplumio.protocol.Protocol.close_writer", new_callable=AsyncMock
    ) as mock_close_writer:
        await dummy_protocol.connection_lost()
        mock_close_writer.assert_awaited_once()

    assert not dummy_protocol.connected.is_set()
    mock_on_connection_lost.assert_awaited_once()

    # Test shutting down the connection.
    with (
        patch("asyncio.Event.is_set", return_value=True),
        patch(
            "pyplumio.protocol.Protocol.close_writer", new_callable=AsyncMock
        ) as mock_close_writer,
    ):
        await dummy_protocol.shutdown()
        mock_close_writer.assert_awaited_once()

    assert not dummy_protocol.connected.is_set()


@pytest.mark.usefixtures("frozen_time")
def test_statistics() -> None:
    """Test statistics dataclass."""
    statistics = Statistics(failed_frames=1)
    assert statistics.connected_since == "never"
    assert statistics.failed_frames == 1
    assert statistics.connection_losses == 0
    assert statistics.connection_loss_at == "never"
    assert statistics.sent_bytes == 0
    assert statistics.sent_frames == 0
    assert statistics.received_bytes == 0
    assert statistics.received_frames == 0
    statistics.update_sent(Request())
    assert statistics.sent_bytes == 10
    assert statistics.sent_frames == 1
    statistics.update_received(Response())
    assert statistics.received_bytes == 10
    assert statistics.received_frames == 1
    statistics.reset_transfer_statistics()
    assert statistics.sent_bytes == 0
    assert statistics.sent_frames == 0
    assert statistics.received_bytes == 0
    assert statistics.received_frames == 0
    assert statistics.failed_frames == 0
    statistics.update_connection_lost()
    assert statistics.connection_losses == 1
    assert statistics.connection_loss_at == datetime.now()


@patch("pyplumio.protocol.AsyncProtocol.create_task")
@patch("pyplumio.protocol.AsyncProtocol.frame_consumer", new_callable=Mock)
@patch("pyplumio.protocol.AsyncProtocol.frame_producer", new_callable=Mock)
@pytest.mark.usefixtures("frozen_time")
def test_async_protocol_connection_established(
    mock_frame_producer, mock_frame_consumer, mock_create_task
) -> None:
    """Test establishing connection with an async protocol."""
    with patch("asyncio.Queue"):
        async_protocol = AsyncProtocol()

    # Create stream reader, stream writer and queue mocks..
    mock_stream_reader = Mock(spec=asyncio.StreamReader)
    mock_stream_writer = Mock(spec=asyncio.StreamWriter)
    mock_read_queue = Mock(spec=asyncio.Queue)
    mock_write_queue = Mock(spec=asyncio.Queue)
    mock_put_nowait = mock_write_queue.put_nowait

    # Create ecoMAX device mock and add it to the protocol.
    mock_ecomax = Mock(spec=EcoMAX, new_callable=Mock)
    async_protocol.data = {"ecomax": mock_ecomax}

    # Test connection established.
    with (
        patch.object(
            async_protocol, "_queues", Queues(mock_read_queue, mock_write_queue)
        ),
        patch(
            "pyplumio.protocol.Statistics.reset_transfer_statistics"
        ) as mock_reset_transfer_statistics,
    ):
        async_protocol.connection_established(mock_stream_reader, mock_stream_writer)

    # Check that StartMaster request was added to the write queue.
    mock_put_nowait.assert_called_once()
    frame = mock_put_nowait.call_args.args[0]
    assert isinstance(frame, StartMasterRequest)
    assert frame.recipient == 69

    # Check that two frame consumers, one write consumer and one frame
    # producer were created.
    assert mock_frame_consumer.call_count == 3
    mock_frame_producer.assert_called_once()
    assert mock_create_task.call_count == 4

    # Check that devices were notified.
    mock_ecomax.dispatch_nowait.assert_called_once_with(ATTR_CONNECTED, True)

    # Check statistics.
    mock_reset_transfer_statistics.assert_called_once()
    assert async_protocol.statistics.connected_since == datetime.now()


async def test_async_protocol_connection_lost() -> None:
    """Test losing the connection with an async protocol."""
    mock_read_queue = Mock(spec=asyncio.Queue)
    mock_write_queue = Mock(spec=asyncio.Queue)

    # Create connection lost callback mock.
    mock_on_connection_lost = AsyncMock()
    async_protocol = AsyncProtocol()
    async_protocol.on_connection_lost.add(mock_on_connection_lost)

    # Create ecoMAX device mock and add it to the protocol.
    mock_ecomax = Mock(spec=EcoMAX, new_callable=AsyncMock)
    mock_writer = AsyncMock(spec=FrameWriter)
    async_protocol.writer = mock_writer
    async_protocol.data = {"ecomax": mock_ecomax}

    # Ensure that on connection lost callback not awaited, when
    # connection is not established.
    await async_protocol.connection_lost()
    async_protocol.connected.set()
    mock_on_connection_lost.assert_not_awaited()

    with patch.object(
        async_protocol, "_queues", Queues(mock_read_queue, mock_write_queue)
    ):
        await async_protocol.connection_lost()

    # Check that devices were notified and callback was called.
    mock_ecomax.dispatch.assert_called_once_with(ATTR_CONNECTED, False)
    mock_on_connection_lost.assert_called_once()

    # Check that writer was closed.
    mock_writer.close.assert_awaited_once()
    assert async_protocol.writer is None


@patch("asyncio.wait_for")
@patch("asyncio.gather", new_callable=AsyncMock)
@patch("pyplumio.protocol.AsyncProtocol.cancel_tasks")
@patch("pyplumio.devices.ecomax.EcoMAX.shutdown", new_callable=Mock)
@patch("pyplumio.helpers.event_manager.EventManager.dispatch", new_callable=Mock)
@pytest.mark.usefixtures("skip_asyncio_events")
async def test_async_protocol_shutdown(
    mock_dispatch,
    mock_shutdown,
    mock_cancel_tasks,
    mock_gather,
    mock_wait_for,
    async_protocol: AsyncProtocol,
) -> None:
    """Test shutting down connection with an async protocol."""
    mock_read_queue = Mock()
    mock_write_queue = Mock()

    mock_writer = AsyncMock(spec=FrameWriter)
    mock_writer.close = AsyncMock()
    async_protocol.writer = mock_writer
    async_protocol.data["ecomax"] = EcoMAX(queue=asyncio.Queue(), network=NetworkInfo())

    mock_frame_consumer_task = Mock(spec=asyncio.Task)
    mock_frame_producer_task = Mock(spec=asyncio.Task)

    with (
        patch.object(
            async_protocol, "_queues", Queues(mock_read_queue, mock_write_queue)
        ),
        patch(
            "pyplumio.protocol.AsyncProtocol.tasks",
            return_value=[
                mock_frame_consumer_task,
                mock_frame_producer_task,
            ],
            new_callable=PropertyMock,
        ),
    ):
        await async_protocol.shutdown()

    mock_cancel_tasks.assert_called_once()
    mock_gather.await_count = 3
    mock_gather.assert_has_awaits(
        [
            call(mock_read_queue.join(), mock_write_queue.join()),
            call(*async_protocol.tasks, return_exceptions=True),
            call(mock_dispatch()),
            call(mock_shutdown()),
        ]
    )
    mock_writer.close.assert_awaited_once()
    assert async_protocol.writer is None


@pytest.mark.usefixtures(
    "skip_asyncio_events", "skip_asyncio_create_task", "frozen_time"
)
async def test_async_protocol_frame_producer(
    async_protocol: AsyncProtocol, caplog
) -> None:
    """Test a frame producer task within an async protocol."""
    success = Response(sender=DeviceType.ECOMAX)
    responses = (
        success,
        ProtocolError("test protocol error"),
        UnknownDeviceError("test unknown device error"),
        UnknownFrameError("test unknown frame error"),
        ReadError("test read error"),
        FrameDataError("test frame data error"),
        Exception("test generic error"),
        ConnectionError,
    )

    # Create mock frame reader and writer.
    mock_reader = AsyncMock(spec=FrameReader)
    mock_reader.read = AsyncMock(side_effect=responses)
    mock_writer = AsyncMock(spec=FrameWriter)

    # Create mock queues.
    mock_read_queue = AsyncMock(spec=asyncio.Queue)
    mock_write_queue = AsyncMock(spec=asyncio.Queue)
    mock_write_queue.empty = Mock(
        side_effect=(
            False,
            *(True for _ in range(len(responses) - 1)),
        )
    )
    request = Request()
    mock_write_queue.get = AsyncMock(return_value=request)

    with (
        patch("pyplumio.devices.ecomax.EcoMAX"),
        patch(
            "pyplumio.protocol.AsyncProtocol.connection_lost", new_callable=Mock
        ) as mock_connection_lost,
        caplog.at_level(logging.DEBUG),
    ):
        await async_protocol.frame_producer(
            Queues(mock_read_queue, mock_write_queue),
            reader=mock_reader,
            writer=mock_writer,
        )

    assert caplog.record_tuples == [
        (
            "pyplumio.protocol",
            logging.DEBUG,
            "Can't process received frame: test protocol error",
        ),
        (
            "pyplumio.protocol",
            logging.DEBUG,
            "Can't process received frame: test unknown device error",
        ),
        (
            "pyplumio.protocol",
            logging.DEBUG,
            "Can't process received frame: test unknown frame error",
        ),
        (
            "pyplumio.protocol",
            logging.DEBUG,
            "Can't process received frame: test read error",
        ),
        (
            "pyplumio.protocol",
            logging.DEBUG,
            "Can't process received frame: test frame data error",
        ),
        (
            "pyplumio.protocol",
            logging.ERROR,
            "Unexpected exception",
        ),
    ]

    mock_writer.write.assert_awaited_once_with(request)
    mock_write_queue.task_done.assert_called_once()
    mock_read_queue.put_nowait.assert_called_once_with(success)
    mock_connection_lost.assert_called_once()
    assert mock_write_queue.get.await_count == 1
    assert mock_write_queue.empty.call_count == 8
    assert mock_reader.read.await_count == 8

    # Check statistics.
    assert asdict(async_protocol.statistics) == {
        "connected_since": "never",
        "received_bytes": 10,
        "received_frames": 1,
        "sent_bytes": 10,
        "sent_frames": 1,
        "failed_frames": 5,
        "connection_losses": 1,
        "connection_loss_at": datetime.now(),
        "devices": set(),
    }


@patch("pyplumio.frames.requests.CheckDeviceRequest.response")
@patch("pyplumio.frames.requests.ProgramVersionRequest.response")
@pytest.mark.usefixtures("skip_asyncio_events")
async def test_async_protocol_frame_consumer(
    mock_program_version_response,
    mock_device_available_response,
    async_protocol: AsyncProtocol,
    caplog,
    frozen_time,
) -> None:
    """Test a frame consumer task within an async protocol."""
    mock_read_queue = Mock(spec=asyncio.Queue)
    mock_write_queue = Mock(spec=asyncio.Queue)
    mock_read_queue.get = AsyncMock()

    with (
        patch.object(
            async_protocol, "_queues", Queues(mock_read_queue, mock_write_queue)
        ),
        patch("asyncio.Lock.acquire", return_value=True) as mock_lock_acquire,
        patch("asyncio.Lock.release") as mock_lock_release,
    ):
        await async_protocol.get_device_entry(DeviceType.ECOMAX)

    mock_lock_acquire.assert_awaited_once()
    mock_lock_release.assert_called_once()

    mock_read_queue.get.side_effect = (
        CheckDeviceRequest(sender=DeviceType.ECOMAX),
        ProgramVersionRequest(sender=DeviceType.ECOMAX),
    )

    with (
        caplog.at_level(logging.DEBUG),
        patch("asyncio.Event.is_set", side_effect=(True, True, False)),
    ):
        await async_protocol.frame_consumer(mock_read_queue)

    await async_protocol.shutdown()

    # Check that network settings is correctly set.
    mock_device_available_response.assert_called_once_with(
        data={
            "network": NetworkInfo(
                eth=EthernetParameters(
                    ip="1.1.1.2",
                    netmask="255.255.255.255",
                    gateway="1.1.1.1",
                    status=True,
                ),
                wlan=WirelessParameters(
                    ip="2.2.2.2",
                    netmask="255.255.255.255",
                    gateway="2.2.2.1",
                    status=True,
                    ssid="test_ssid",
                    encryption=EncryptionType.WPA2,
                    signal_quality=50,
                ),
                server_status=True,
            )
        }
    )

    mock_write_queue.put_nowait.assert_has_calls(
        [
            call(mock_device_available_response()),
            call(mock_program_version_response()),
        ]
    )
    assert mock_read_queue.task_done.call_count == 2

    # Test statistics.
    connected_since = datetime.now()
    frozen_time.tick(timedelta(seconds=10))
    ecomax = cast(EcoMAX, async_protocol.get_nowait("ecomax"))
    await ecomax.dispatch(ATTR_REGDATA, True)
    assert asdict(async_protocol.statistics.devices.pop()) == {
        "address": DeviceType.ECOMAX,
        "connected_since": connected_since,
        "last_seen": datetime.now(),
    }
