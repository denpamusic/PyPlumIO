"""Contains tests for the protocol classes."""

import asyncio
import logging
from unittest.mock import AsyncMock, Mock, PropertyMock, call, patch

import pytest

from pyplumio.const import ATTR_CONNECTED, DeviceType, EncryptionType
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.exceptions import (
    FrameDataError,
    FrameError,
    ReadError,
    UnknownDeviceError,
)
from pyplumio.frames import Response
from pyplumio.frames.requests import (
    CheckDeviceRequest,
    ProgramVersionRequest,
    StartMasterRequest,
)
from pyplumio.protocol import AsyncProtocol, DummyProtocol
from pyplumio.stream import FrameReader, FrameWriter
from pyplumio.structures.network_info import (
    EthernetParameters,
    NetworkInfo,
    WirelessParameters,
)

UNKNOWN_DEVICE: int = 99


@pytest.fixture()
def bypass_asyncio_create_task():
    """Bypass asyncio create task."""
    with patch("asyncio.create_task"):
        yield


@pytest.fixture(name="bypass_asyncio_events")
def fixture_bypass_asyncio_events():
    """Bypass asyncio events."""
    with patch("asyncio.Event.wait", new_callable=AsyncMock), patch(
        "asyncio.Event.is_set", return_value=True
    ):
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
    mock_connection_lost_callback = AsyncMock()
    dummy_protocol = DummyProtocol(
        connection_lost_callback=mock_connection_lost_callback
    )

    mock_reader = AsyncMock(spec=asyncio.StreamReader)
    mock_writer = AsyncMock(spec=asyncio.StreamWriter, new_callable=Mock)

    # Test establishing the connection.
    with patch("pyplumio.protocol.FrameReader") as mock_frame_reader, patch(
        "pyplumio.protocol.FrameWriter"
    ) as mock_frame_writer:
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
    mock_connection_lost_callback.assert_awaited_once()

    # Test shutting down the connection.
    with patch("asyncio.Event.is_set", return_value=True), patch(
        "pyplumio.protocol.Protocol.close_writer", new_callable=AsyncMock
    ) as mock_close_writer:
        await dummy_protocol.shutdown()
        mock_close_writer.assert_awaited_once()

    assert not dummy_protocol.connected.is_set()


@patch("pyplumio.protocol.AsyncProtocol.create_task")
@patch("pyplumio.protocol.AsyncProtocol.frame_consumer", new_callable=Mock)
@patch("pyplumio.protocol.AsyncProtocol.frame_producer", new_callable=Mock)
def test_async_protocol_connection_established(
    mock_frame_producer, mock_frame_consumer, mock_create_task
) -> None:
    """Test establishing connection with an async protocol."""
    with patch("asyncio.Queue") as mock_queue:
        async_protocol = AsyncProtocol()

    # Check queues property.
    assert async_protocol.queues == (mock_queue.return_value, mock_queue.return_value)

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
    with patch(
        "pyplumio.protocol.AsyncProtocol.queues",
        return_value=(mock_read_queue, mock_write_queue),
        new_callable=PropertyMock,
    ):
        async_protocol.connection_established(mock_stream_reader, mock_stream_writer)

    # Check that StartMaster request was added to the write queue.
    mock_put_nowait.assert_called_once()
    frame = mock_put_nowait.call_args.args[0]
    assert isinstance(frame, StartMasterRequest)
    assert frame.recipient == 69

    # Check that two frame consumers, one write consumer and one frame
    # producer were created.
    assert mock_frame_consumer.call_count == 2
    mock_frame_producer.assert_called_once()
    assert mock_create_task.call_count == 3

    # Check that devices were notified.
    mock_ecomax.dispatch_nowait.assert_called_once_with(ATTR_CONNECTED, True)


async def test_async_protocol_connection_lost(bypass_asyncio_events) -> None:
    """Test losing the connection with an async protocol."""
    mock_read_queue = Mock(spec=asyncio.Queue)
    mock_write_queue = Mock(spec=asyncio.Queue)

    # Create connection lost callback mock.
    mock_connection_lost_callback = AsyncMock()
    async_protocol = AsyncProtocol(
        connection_lost_callback=mock_connection_lost_callback
    )

    # Create ecoMAX device mock and add it to the protocol.
    mock_ecomax = Mock(spec=EcoMAX, new_callable=AsyncMock)
    mock_writer = AsyncMock()
    mock_writer.close = AsyncMock()
    async_protocol.writer = mock_writer
    async_protocol.data = {"ecomax": mock_ecomax}
    async_protocol.writer = mock_writer

    with patch(
        "pyplumio.protocol.AsyncProtocol.queues",
        return_value=(mock_read_queue, mock_write_queue),
        new_callable=PropertyMock,
    ):
        await async_protocol.connection_lost()

    # Check that devices were notified and callback was called.
    mock_ecomax.dispatch.assert_called_once_with(ATTR_CONNECTED, False)
    mock_connection_lost_callback.assert_called_once()

    # Check that writer was closed.
    mock_writer.close.assert_awaited_once()
    assert async_protocol.writer is None


@patch("asyncio.wait")
@patch("asyncio.gather", new_callable=AsyncMock)
@patch("pyplumio.protocol.AsyncProtocol.cancel_tasks")
@patch("pyplumio.devices.ecomax.EcoMAX.shutdown")
async def test_async_protocol_shutdown(
    mock_shutdown,
    mock_cancel_tasks,
    mock_gather,
    mock_wait,
    async_protocol: AsyncProtocol,
    bypass_asyncio_events,
) -> None:
    """Test shutting down connection with an async protocol."""
    mock_read_queue = Mock()
    mock_write_queue = Mock()

    mock_writer = AsyncMock()
    mock_writer.close = AsyncMock(side_effect=OSError)
    async_protocol.writer = mock_writer
    async_protocol.data["ecomax"] = EcoMAX(queue=asyncio.Queue(), network=NetworkInfo())

    mock_frame_consumer_task = Mock()
    mock_frame_producer_task = Mock()

    with patch(
        "pyplumio.protocol.AsyncProtocol.queues",
        return_value=(mock_read_queue, mock_write_queue),
        new_callable=PropertyMock,
    ), patch(
        "pyplumio.protocol.AsyncProtocol.tasks",
        return_value=[
            mock_frame_consumer_task,
            mock_frame_producer_task,
        ],
        new_callable=PropertyMock,
    ):
        await async_protocol.shutdown()

    mock_shutdown.assert_awaited_once()
    mock_cancel_tasks.assert_called_once()
    assert mock_gather.call_count == 2
    calls = [
        call(mock_read_queue.join(), mock_write_queue.join()),
        call(*async_protocol.tasks, return_exceptions=True),
    ]
    mock_gather.assert_has_awaits(calls)
    mock_writer.close.assert_awaited_once()
    assert async_protocol.writer is None


@pytest.mark.usefixtures("bypass_asyncio_create_task")
async def test_async_protocol_frame_producer(
    async_protocol: AsyncProtocol, bypass_asyncio_events, caplog
) -> None:
    """Test a frame producer task within an async protocol."""
    response = Response(sender=DeviceType.ECOMAX)

    # Create mock frame reader and writer.
    async_protocol.reader = AsyncMock(spec=FrameReader)
    async_protocol.reader.read = AsyncMock(
        side_effect=(
            response,
            FrameError("test frame error"),
            UnknownDeviceError("test unknown device error"),
            ReadError("test read error"),
            FrameDataError("test frame data error"),
            Exception("test generic error"),
            ConnectionError,
        )
    )

    async_protocol.writer = AsyncMock(spec=FrameWriter)

    # Create mock queues.
    mock_read_queue = AsyncMock(spec=asyncio.Queue)
    mock_write_queue = AsyncMock(spec=asyncio.Queue)
    mock_write_queue.qsize = Mock(side_effect=(1, 0, 0, 0, 0, 0, 0))
    mock_write_queue.get = AsyncMock(return_value="test_request")

    with patch("pyplumio.devices.ecomax.EcoMAX") as mock_device, patch(
        "pyplumio.protocol.AsyncProtocol.connection_lost", new_callable=Mock
    ) as mock_connection_lost, caplog.at_level(logging.DEBUG):
        await async_protocol.frame_producer(mock_read_queue, mock_write_queue)

    assert caplog.record_tuples == [
        (
            "pyplumio.protocol",
            logging.DEBUG,
            "Can't process received frame: test frame error",
        ),
        (
            "pyplumio.protocol",
            logging.DEBUG,
            "Unknown device: test unknown device error",
        ),
        (
            "pyplumio.protocol",
            logging.DEBUG,
            "Read error: test read error",
        ),
        (
            "pyplumio.protocol",
            logging.WARNING,
            "Incorrect payload: test frame data error",
        ),
        (
            "pyplumio.protocol",
            logging.ERROR,
            "test generic error",
        ),
    ]

    async_protocol.writer.write.assert_awaited_once_with("test_request")
    mock_write_queue.task_done.assert_called_once()
    mock_read_queue.put_nowait.assert_called_once_with(
        (mock_device.return_value, response)
    )
    mock_connection_lost.assert_called_once()
    assert mock_write_queue.get.await_count == 1
    assert mock_write_queue.qsize.call_count == 7
    assert async_protocol.reader.read.await_count == 7


@patch("pyplumio.frames.requests.CheckDeviceRequest.response")
@patch("pyplumio.frames.requests.ProgramVersionRequest.response")
async def test_async_protocol_frame_consumer(
    mock_program_version_response,
    mock_device_available_response,
    bypass_asyncio_events,
    async_protocol: AsyncProtocol,
    caplog,
) -> None:
    """Test a frame consumer task within an async protocol."""
    mock_read_queue = Mock(spec=asyncio.Queue)
    mock_write_queue = Mock(spec=asyncio.Queue)
    mock_read_queue.get = AsyncMock()

    with patch(
        "pyplumio.protocol.AsyncProtocol.queues",
        return_value=(mock_read_queue, mock_write_queue),
    ) as mock_queues:
        ecomax = async_protocol.setup_device_entry(DeviceType.ECOMAX)

    mock_read_queue.get.side_effect = (
        (ecomax, CheckDeviceRequest()),
        (ecomax, ProgramVersionRequest()),
    )

    with caplog.at_level(logging.DEBUG), patch(
        "asyncio.Event.is_set", side_effect=(True, True, False)
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

    mock_queues[1].put_nowait.assert_has_calls(
        [
            call(mock_device_available_response()),
            call(mock_program_version_response()),
        ]
    )
    assert mock_read_queue.task_done.call_count == 2
