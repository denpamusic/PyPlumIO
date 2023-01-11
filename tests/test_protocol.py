"""Contains tests for protocol."""

import asyncio
import logging
from unittest.mock import AsyncMock, Mock, PropertyMock, call, patch

import pytest

from pyplumio.const import DeviceType
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.exceptions import FrameError, ReadError, UnknownFrameError
from pyplumio.frames.requests import (
    CheckDeviceRequest,
    ProgramVersionRequest,
    StartMasterRequest,
)
from pyplumio.helpers.network_info import (
    WLAN_ENCRYPTION_WPA2,
    EthernetParameters,
    NetworkInfo,
    WirelessParameters,
)
from pyplumio.protocol import Protocol
from pyplumio.stream import FrameReader, FrameWriter
from tests.test_devices import UNKNOWN_DEVICE


@pytest.fixture(name="protocol")
def fixture_protocol() -> Protocol:
    """Return protocol instance."""
    return Protocol(
        wireless_parameters=WirelessParameters(
            ssid="test_ssid",
            ip="2.2.2.2",
            encryption=WLAN_ENCRYPTION_WPA2,
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


@patch("pyplumio.protocol.Protocol.create_task")
@patch("pyplumio.protocol.Protocol.frame_consumer", new_callable=Mock)
@patch("pyplumio.protocol.Protocol.write_consumer", new_callable=Mock)
@patch("pyplumio.protocol.Protocol.frame_producer", new_callable=Mock)
def test_connection_established(
    mock_frame_producer,
    mock_write_consumer,
    mock_frame_consumer,
    mock_create_task,
) -> None:
    """Test Protocol object initialization."""
    # Test queue getter.
    with patch("asyncio.Queue") as mock_queue:
        protocol = Protocol()

    # Check queues property.
    assert protocol.queues == (mock_queue.return_value, mock_queue.return_value)

    # Create stream reader, stream writer and queue mocks..
    mock_stream_reader = Mock(spec=asyncio.StreamReader)
    mock_stream_writer = Mock(spec=asyncio.StreamWriter)
    mock_read_queue = Mock(spec=asyncio.Queue)
    mock_write_queue = Mock(spec=asyncio.Queue)
    mock_put_nowait = mock_write_queue.put_nowait

    # Test connection established.
    with patch(
        "pyplumio.protocol.Protocol.queues",
        return_value=(mock_read_queue, mock_write_queue),
        new_callable=PropertyMock,
    ):
        protocol.connection_established(mock_stream_reader, mock_stream_writer)

    # Check that StartMaster request was added to the write queue.
    mock_put_nowait.assert_called_once()
    frame = mock_put_nowait.call_args.args[0]
    assert isinstance(frame, StartMasterRequest)
    assert frame.recipient == 69

    # Check that two frame consumers, one write consumer and one frame
    # producer were created.
    assert mock_frame_consumer.call_count == 2
    mock_frame_producer.assert_called_once()
    mock_write_consumer.assert_called_once()
    assert mock_create_task.call_count == 4


@patch("pyplumio.protocol.Protocol.connection_lost", new_callable=Mock)
async def test_frame_producer(
    mock_connection_lost,
    bypass_asyncio_create_task,
    bypass_asyncio_events,
    protocol: Protocol,
    caplog,
) -> None:
    """Test frame producer task."""
    mock_lock = AsyncMock(spec=asyncio.Lock)

    # Create mock frame reader.
    protocol.reader = Mock(spec=FrameReader)
    protocol.reader.read = AsyncMock()
    protocol.reader.read.side_effect = (
        "test",
        UnknownFrameError("test unknown frame error"),
        FrameError("test frame error"),
        ReadError("test read error"),
        Exception("test generic error"),
        ConnectionError,
    )

    # Create mock read queue.
    mock_read_queue = AsyncMock(spec=asyncio.Queue)
    mock_read_queue.put_nowait = Mock()

    with caplog.at_level(logging.DEBUG):
        await protocol.frame_producer(mock_read_queue, mock_lock)

    assert caplog.record_tuples == [
        (
            "pyplumio.protocol",
            logging.DEBUG,
            "Unknown frame type: test unknown frame error",
        ),
        (
            "pyplumio.protocol",
            logging.WARNING,
            "Can't process received frame: test frame error",
        ),
        (
            "pyplumio.protocol",
            logging.DEBUG,
            "Read error: test read error",
        ),
        (
            "pyplumio.protocol",
            logging.ERROR,
            "test generic error",
        ),
    ]

    mock_read_queue.put_nowait.assert_called_once_with("test")
    assert protocol.reader.read.await_count == 6
    assert mock_lock.acquire.await_count == 6
    assert mock_lock.release.call_count == 6


@patch("pyplumio.protocol.Protocol.connection_lost", new_callable=Mock)
async def test_write_consumer(
    mock_connection_lost,
    bypass_asyncio_create_task,
    bypass_asyncio_events,
    bypass_asyncio_sleep,
    protocol: Protocol,
) -> None:
    """Test write consumer task."""
    mock_lock = AsyncMock(spec=asyncio.Lock)

    # Create mock frame writer.
    protocol.writer = Mock(spec=FrameWriter)
    protocol.writer.write = AsyncMock()
    protocol.writer.write.side_effect = ("test", ConnectionError)

    # Create mock write queue.
    mock_write_queue = Mock(spec=asyncio.Queue)
    mock_write_queue.get = AsyncMock()
    mock_write_queue.get.side_effect = ("test", "test")

    await protocol.write_consumer(mock_write_queue, mock_lock)
    calls = [call("test"), call("test")]
    protocol.writer.write.assert_has_calls(calls)
    assert protocol.writer.write.await_count == 2
    assert mock_lock.acquire.await_count == 2
    assert mock_lock.release.call_count == 2


@patch("pyplumio.frames.requests.CheckDeviceRequest.response")
@patch("pyplumio.frames.requests.ProgramVersionRequest.response")
@patch("pyplumio.protocol.Addressable.handle_frame")
async def test_frame_consumer(
    mock_handle_frame,
    mock_program_version_response,
    mock_device_available_response,
    bypass_asyncio_events,
    protocol: Protocol,
    caplog,
) -> None:
    """Test frame consumer task."""
    # Create mock queues.
    mock_read_queue = Mock(spec=asyncio.Queue)
    mock_write_queue = Mock(spec=asyncio.Queue)
    mock_read_queue.get = AsyncMock()
    mock_read_queue.get.side_effect = (
        CheckDeviceRequest(sender=DeviceType.ECOMAX),
        ProgramVersionRequest(sender=DeviceType.ECOMAX),
        CheckDeviceRequest(sender=UNKNOWN_DEVICE),
        RuntimeError("break loop"),
    )

    with pytest.raises(RuntimeError), caplog.at_level(logging.DEBUG):
        await protocol.frame_consumer(mock_read_queue, mock_write_queue)

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
                    encryption=4,
                    signal_quality=50,
                ),
                server_status=True,
            )
        }
    )

    # Check that unknown device exception was raised for device
    # with address 99.
    assert "Unknown device (99)" in caplog.text
    calls = [
        call(mock_device_available_response()),
        call(mock_program_version_response()),
    ]
    mock_write_queue.put_nowait.assert_has_calls(calls)
    assert mock_handle_frame.call_count == 2
    assert mock_read_queue.task_done.call_count == 3


async def test_connection_lost(bypass_asyncio_events) -> None:
    """Test connection lost callback."""
    # Create mock queues.
    mock_read_queue = Mock(spec=asyncio.Queue)
    mock_write_queue = Mock(spec=asyncio.Queue)

    # Create connection lost callback mock.
    mock_connection_lost_callback = AsyncMock()
    protocol = Protocol(connection_lost_callback=mock_connection_lost_callback)

    with patch(
        "pyplumio.protocol.Protocol.queues",
        return_value=(mock_read_queue, mock_write_queue),
        new_callable=PropertyMock,
    ):
        await protocol.connection_lost()

    mock_connection_lost_callback.assert_called_once()


@patch("asyncio.wait")
@patch("asyncio.gather", new_callable=AsyncMock)
@patch("pyplumio.protocol.Protocol.cancel_tasks")
@patch("pyplumio.devices.ecomax.EcoMAX.shutdown")
async def test_shutdown(
    mock_shutdown,
    mock_cancel_tasks,
    mock_gather,
    mock_wait,
    bypass_asyncio_create_task,
    protocol: Protocol,
) -> None:
    """Test protocol shutdown."""
    # Create mock queues.
    mock_read_queue = Mock()
    mock_write_queue = Mock()

    protocol.writer = Mock()
    protocol.writer.close = AsyncMock()
    protocol.devices["ecomax"] = EcoMAX(queue=asyncio.Queue())

    mock_write_consumer_task = Mock()
    mock_frame_consumer_task = Mock()
    mock_frame_producer_task = Mock()

    with patch(
        "pyplumio.protocol.Protocol.queues",
        return_value=(mock_read_queue, mock_write_queue),
        new_callable=PropertyMock,
    ), patch(
        "pyplumio.protocol.Protocol.tasks",
        return_value=[
            mock_write_consumer_task,
            mock_frame_consumer_task,
            mock_frame_producer_task,
        ],
        new_callable=PropertyMock,
    ):

        await protocol.shutdown()

    mock_shutdown.assert_awaited_once()
    mock_cancel_tasks.assert_called_once()
    assert mock_gather.call_count == 2
    calls = [
        call(mock_read_queue.join(), mock_write_queue.join()),
        call(*protocol.tasks, return_exceptions=True),
    ]
    mock_gather.assert_has_awaits(calls)
    protocol.writer.close.assert_awaited_once()


async def test_get_device(protocol: Protocol):
    """Test wait for device method."""
    # Test that event is being created on get device call.
    mock_ecomax = AsyncMock(spec=EcoMAX)
    mock_event = AsyncMock(spec=asyncio.Event)
    with pytest.raises(KeyError), patch(
        "pyplumio.protocol.Protocol.create_event",
        return_value=mock_event,
    ) as mock_create_event:
        mock_create_event.wait = AsyncMock()
        await protocol.get_device("ecomax")

    mock_create_event.assert_called_once_with("ecomax")
    mock_event.wait.assert_awaited_once()

    protocol.devices["ecomax"] = mock_ecomax
    assert protocol.ecomax == mock_ecomax

    # Check that exception is raised on nonexistent device.
    with pytest.raises(AttributeError):
        print(protocol.nonexistent)
