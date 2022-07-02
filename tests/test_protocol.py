"""Contains tests for protocol."""

import logging
from unittest.mock import AsyncMock, Mock, PropertyMock, call, patch

import pytest

from pyplumio.const import ECOMAX_ADDRESS
from pyplumio.devices import EcoMAX
from pyplumio.exceptions import FrameError, ReadError, UnknownFrameError
from pyplumio.frames.requests import CheckDevice, ProgramVersion, StartMaster
from pyplumio.helpers.network_info import (
    WLAN_ENCRYPTION_WPA2,
    EthernetParameters,
    NetworkInfo,
    WirelessParameters,
)
from pyplumio.protocol import Protocol
from tests.test_devices import UNKNOWN_DEVICE


@pytest.fixture(name="protocol")
def fixture_protocol() -> Protocol:
    """Return protocol instance."""
    return Protocol()


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
    mock_stream_reader = Mock()
    mock_stream_writer = Mock()
    mock_read_queue = Mock()
    mock_write_queue = Mock()
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
    assert isinstance(frame, StartMaster)
    assert frame.recipient == 69

    # Check that two frame consumers, one write consumer and one frame
    # producer were created.
    assert mock_frame_consumer.call_count == 2
    mock_frame_producer.assert_called_once()
    mock_write_consumer.assert_called_once()
    assert mock_create_task.call_count == 4


@patch("pyplumio.protocol.Protocol.connection_lost", new_callable=Mock)
async def test_frame_producer(
    mock_connection_lost, bypass_asyncio_create_task, protocol: Protocol, caplog
) -> None:
    """Test frame producer task."""
    mock_lock = AsyncMock()

    # Create mock frame reader.
    protocol.reader = Mock()
    protocol.reader.read = AsyncMock()
    protocol.reader.read.side_effect = (
        "test",
        UnknownFrameError("test unknown frame error"),
        ReadError("test read error"),
        FrameError("test frame error"),
        ConnectionError,
    )

    # Create mock read queue.
    mock_read_queue = AsyncMock()
    mock_read_queue.put_nowait = Mock()

    with caplog.at_level(logging.DEBUG):
        await protocol.frame_producer(mock_read_queue, mock_lock)

    assert caplog.record_tuples == [
        (
            "pyplumio.protocol",
            logging.DEBUG,
            "UnknownFrameError: test unknown frame error",
        ),
        ("pyplumio.protocol", logging.DEBUG, "ReadError: test read error"),
        ("pyplumio.protocol", logging.WARNING, "FrameError: test frame error"),
    ]

    mock_read_queue.put_nowait.assert_called_once_with("test")
    assert protocol.reader.read.await_count == 5
    assert mock_lock.__aenter__.await_count == 5


@patch("pyplumio.protocol.Protocol.connection_lost", new_callable=Mock)
async def test_write_consumer(
    mock_connection_lost, bypass_asyncio_create_task, protocol: Protocol
) -> None:
    """Test write consumer task."""
    mock_lock = AsyncMock()

    # Create mock frame writer.
    protocol.writer = Mock()
    protocol.writer.write = AsyncMock()
    protocol.writer.write.side_effect = ("test", ConnectionError)

    # Create mock write queue.
    mock_write_queue = Mock()
    mock_write_queue.get = AsyncMock()
    mock_write_queue.get.side_effect = ("test", "test")

    await protocol.write_consumer(mock_write_queue, mock_lock)
    calls = [call("test"), call("test")]
    protocol.writer.write.assert_has_calls(calls)
    assert protocol.writer.write.await_count == 2
    assert mock_lock.__aenter__.await_count == 2


@patch("pyplumio.frames.requests.CheckDevice.response")
@patch("pyplumio.frames.requests.ProgramVersion.response")
@patch("pyplumio.protocol.Device.handle_frame")
async def test_frame_consumer(
    mock_handle_frame,
    mock_program_version_response,
    mock_device_available_response,
    protocol: Protocol,
    caplog,
) -> None:
    """Test frame consumer task."""
    # Create mock queues.
    mock_read_queue = Mock()
    mock_write_queue = Mock()
    mock_read_queue.get = AsyncMock()
    mock_read_queue.get.side_effect = (
        CheckDevice(sender=ECOMAX_ADDRESS),
        ProgramVersion(sender=ECOMAX_ADDRESS),
        CheckDevice(sender=UNKNOWN_DEVICE),
        RuntimeError("break loop"),
    )

    # Set eth and wlan parameters.
    protocol.set_eth("1.1.1.2", "255.255.255.255", "1.1.1.1")
    protocol.set_wlan(
        "test_ssid", "2.2.2.2", WLAN_ENCRYPTION_WPA2, "255.255.255.255", "2.2.2.1", 50
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
                    quality=50,
                ),
                server_status=True,
            )
        }
    )

    # Check that unknown device exception was raised for device
    # with address 99.
    assert "Unknown device: 99" in caplog.text
    calls = [
        call(mock_device_available_response()),
        call(mock_program_version_response()),
    ]
    mock_write_queue.put_nowait.assert_has_calls(calls)
    assert mock_handle_frame.call_count == 2
    assert mock_read_queue.task_done.call_count == 3


@patch("pyplumio.protocol.Protocol.shutdown")
async def test_connection_lost(mock_shutdown) -> None:
    """Test connection lost callback."""
    # Create mock queues.
    mock_read_queue = Mock()
    mock_write_queue = Mock()
    mock_read_queue.qsize.return_value = 1
    mock_write_queue.qsize.return_value = 1

    # Create connection lost callback mock.
    mock_connection_lost_callback = AsyncMock()
    protocol = Protocol(connection_lost_callback=mock_connection_lost_callback)

    with patch(
        "pyplumio.protocol.Protocol.queues",
        return_value=(mock_read_queue, mock_write_queue),
        new_callable=PropertyMock,
    ):
        await protocol.connection_lost()

    # Check that _clean_queue method was called.
    for queue in (mock_read_queue, mock_write_queue):
        getattr(queue, "qsize").assert_called_once()
        getattr(queue, "get_nowait").assert_called_once()
        getattr(queue, "task_done").assert_called_once()

    mock_connection_lost_callback.assert_called_once()
    mock_shutdown.assert_called_once()


@patch("asyncio.wait")
@patch("asyncio.gather", new_callable=AsyncMock)
async def test_shutdown(
    mock_gather,
    mock_wait,
    bypass_asyncio_create_task,
    protocol: Protocol,
) -> None:
    """f"""
    # Create mock queues.
    mock_read_queue = Mock()
    mock_write_queue = Mock()

    # Create mock tasks.
    mock_write_consumer_task = Mock()
    mock_frame_consumer_task = Mock()
    mock_frame_producer_task = Mock()
    mock_tasks = (
        mock_write_consumer_task,
        mock_frame_consumer_task,
        mock_frame_producer_task,
    )

    protocol.writer = Mock()
    protocol.writer.close = AsyncMock()
    mock_writer_close = protocol.writer.close

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

    for task in mock_tasks:
        task.cancel.assert_called_once()

    mock_gather.assert_called_once_with(*mock_tasks, return_exceptions=True)
    mock_wait.assert_called_once_with([mock_read_queue.join(), mock_write_queue.join()])
    mock_writer_close.assert_awaited_once()


async def test_get_device(protocol: Protocol):
    """Test wait for device method."""
    with pytest.raises(RuntimeError), patch(
        "asyncio.sleep",
        side_effect=(None, RuntimeError("break loop")),
        new_callable=AsyncMock,
    ) as mock_sleep:
        device = await protocol.get_device("ecomax")

    assert mock_sleep.await_count == 2

    ecomax = EcoMAX(queue=Mock())
    protocol.devices["ecomax"] = ecomax
    with patch(
        "asyncio.sleep",
        new_callable=AsyncMock,
    ) as mock_sleep:
        device = await protocol.get_device("ecomax")

    assert device == ecomax
