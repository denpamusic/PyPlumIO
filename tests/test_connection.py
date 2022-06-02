"""Test PyPlumIO connection."""

import asyncio
from asyncio import StreamReader, StreamWriter
import logging
from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest
from serial import SerialException
from serial_asyncio import serial

from pyplumio.connection import SerialConnection, TcpConnection
from pyplumio.constants import ECOMAX_ADDRESS
from pyplumio.exceptions import ConnectionFailedError, FrameError, FrameTypeError
from pyplumio.frames import requests
from pyplumio.frames.messages import CurrentData
from pyplumio.frames.requests import CheckDevice, ProgramVersion
from pyplumio.frames.responses import (
    UID,
    BoilerParameters,
    DataSchema,
    MixerParameters,
    Password,
)
from pyplumio.helpers.network_info import (
    WLAN_ENCRYPTION_WPA,
    EthernetParameters,
    NetworkInfo,
    WirelessParameters,
)
from pyplumio.helpers.product_info import ProductInfo
from pyplumio.stream import FrameReader, FrameWriter


@pytest.fixture(name="tcp_connection")
def fixture_tcp_connection() -> TcpConnection:
    """Return instance of tcp connection."""
    with TcpConnection(host="1.1.1.1", port=8888) as c:
        return c


@pytest.fixture(name="serial_connection")
def fixture_serial_connection() -> SerialConnection:
    return SerialConnection(device="/dev/ttyUSB0")


def test_tcp_connection_repr(tcp_connection: TcpConnection) -> None:
    """Test serializable tcp connection representation."""
    assert (
        repr(tcp_connection)
        == """TcpConnection(
    host = 1.1.1.1,
    port = 8888,
    kwargs = {}
)
"""
    )


def test_serial_connection_repr(serial_connection: SerialConnection) -> None:
    """Test serializable serial connection representation."""
    assert (
        repr(serial_connection)
        == """SerialConnection(
    device = /dev/ttyUSB0,
    baudrate = 115200,
    kwargs = {}
)
"""
    )


@pytest.mark.asyncio
async def test_tcp_connection_connect(
    tcp_connection: TcpConnection, bypass_asyncio_connection
) -> None:
    """Test tcp connection routine."""
    reader, writer = await tcp_connection.connect()
    assert isinstance(reader, FrameReader)
    assert isinstance(writer, FrameWriter)
    bypass_asyncio_connection.assert_called_once_with(host="1.1.1.1", port=8888)


@pytest.mark.asyncio
async def test_serial_connection_connect(
    serial_connection: SerialConnection, bypass_serial_asyncio_connection
) -> None:
    """Test serial connection routine."""
    reader, writer = await serial_connection.connect()
    assert isinstance(reader, FrameReader)
    assert isinstance(writer, FrameWriter)
    bypass_serial_asyncio_connection.assert_called_once_with(
        url="/dev/ttyUSB0",
        baudrate=115200,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
    )


def test_connection_run(tcp_connection: TcpConnection) -> None:
    """Test connection run."""
    callback = AsyncMock()

    with patch("sys.platform", "win32"), patch(
        "asyncio.WindowsSelectorEventLoopPolicy", create=True, return_value=1
    ), patch("pyplumio.connection.TcpConnection.task") as mock_task, patch(
        "asyncio.set_event_loop_policy",
    ) as mock_set_policy, pytest.raises(
        SystemExit
    ):
        tcp_connection.run(callback)

    mock_task.assert_called_once_with(callback, 1, True)
    mock_set_policy.assert_called_once_with(1)


def test_connection_run_keyboard_interrupt(tcp_connection: TcpConnection) -> None:
    """Test keyboard interrupt with connection run."""
    callback = AsyncMock()

    with patch("pyplumio.connection.TcpConnection.task") as mock_task, patch(
        "sys.exit", side_effect=KeyboardInterrupt
    ):
        tcp_connection.run(callback)

    mock_task.assert_called_once_with(callback, 1, True)


@pytest.mark.asyncio
async def test_connection_task(
    tcp_connection: TcpConnection, caplog, bypass_asyncio_connection, mock_stream_writer
) -> None:
    """Test connection task."""
    # Setup mocks for stream reader and writer and callbacks.
    mock_callback = AsyncMock()
    mock_callback.side_effect = Exception("test error")
    mock_closed_callback = AsyncMock()

    # Add callback to be called on connection close.
    tcp_connection.on_closed(mock_closed_callback)

    with patch(
        "pyplumio.stream.FrameWriter.process_queue",
        side_effect=tcp_connection.async_close,
    ):
        await tcp_connection.task(mock_callback, interval=5)

    # Check that start master command was written.
    mock_stream_writer.write.assert_called_once_with(
        requests.StartMaster(recipient=ECOMAX_ADDRESS).bytes
    )

    # Check that callbacks was called and connection was closed.
    mock_callback.assert_called_once_with(tcp_connection.devices, tcp_connection)
    mock_stream_writer.close.assert_called_once()
    mock_closed_callback.assert_called_once()
    assert tcp_connection.closed
    assert caplog.record_tuples == [
        ("pyplumio.connection", logging.ERROR, "Callback error: test error")
    ]


@pytest.mark.asyncio
async def test_read_frame_type_error(
    tcp_connection: TcpConnection, bypass_asyncio_connection, caplog
) -> None:
    """Test frame type error on read."""
    caplog.set_level(logging.DEBUG)

    with patch(
        "pyplumio.stream.FrameWriter.process_queue",
        side_effect=tcp_connection.async_close,
    ), patch("pyplumio.stream.FrameReader.read", side_effect=FrameTypeError(1)):
        await tcp_connection.task(AsyncMock())

    assert caplog.record_tuples == [
        ("pyplumio.connection", logging.DEBUG, "Type error: 1")
    ]


@pytest.mark.asyncio
async def test_read_frame_error(
    tcp_connection: TcpConnection, bypass_asyncio_connection, caplog
) -> None:
    """Test frame error on read."""
    caplog.set_level(logging.DEBUG)

    with patch(
        "pyplumio.stream.FrameWriter.process_queue",
        side_effect=tcp_connection.async_close,
    ), patch("pyplumio.stream.FrameReader.read", side_effect=FrameError("test_error")):
        await tcp_connection.task(AsyncMock())

    assert caplog.record_tuples == [
        ("pyplumio.connection", logging.WARNING, "Frame error: test_error")
    ]


@pytest.mark.asyncio
async def test_read_connection_error(
    tcp_connection: TcpConnection, bypass_asyncio_connection, caplog
) -> None:
    """Test connection error on connect."""

    # Check with all possible exceptions.
    for exception in (
        asyncio.TimeoutError,
        ConnectionRefusedError,
        ConnectionResetError,
        OSError,
        SerialException,
    ):
        with patch(
            "pyplumio.connection.TcpConnection.connect",
            side_effect=exception,
        ), pytest.raises(ConnectionFailedError):
            await tcp_connection.task(
                AsyncMock(), interval=1, reconnect_on_failure=False
            )


@pytest.mark.asyncio
async def test_read_connection_reconnect(
    tcp_connection: TcpConnection,
    mock_stream_reader: StreamReader,
    mock_stream_writer: StreamWriter,
    bypass_asyncio_connection,
    bypass_asyncio_sleep,
    bypass_asyncio_create_task,
    caplog,
) -> None:
    """Test connection reconnect."""

    # Patch connection so that it returns error on first connection try.
    with patch(
        "pyplumio.connection.TcpConnection.connect",
        side_effect=[
            ConnectionRefusedError,
            (FrameReader(mock_stream_reader), FrameWriter(mock_stream_writer)),
        ],
    ), patch("pyplumio.stream.FrameWriter.write"), patch(
        "pyplumio.connection.TcpConnection._read", return_value=False
    ) as mock_read:
        await tcp_connection.task(AsyncMock())

    # Check that log has reconnect message and attempt has been made.
    assert caplog.record_tuples == [
        (
            "pyplumio.connection",
            logging.ERROR,
            "Connection to device failed, retrying in 20 seconds...",
        )
    ]
    mock_read.assert_called_once()


@pytest.mark.asyncio
async def test_process_unknown_sender(
    tcp_connection: TcpConnection, bypass_asyncio_connection
) -> None:
    """Test processing of the frame with unknown sender."""
    with patch(
        "pyplumio.stream.FrameWriter.process_queue",
        side_effect=tcp_connection.async_close,
    ), patch(
        "pyplumio.stream.FrameReader.read",
        return_value=CheckDevice(sender=0x0),
    ), patch(
        "pyplumio.devices.DevicesCollection.has",
        return_value=False,
    ) as mock_has_device:
        await tcp_connection.task(AsyncMock())

    mock_has_device.assert_called_once_with(0x0)


@pytest.mark.asyncio
async def test_process_program_version_request(
    tcp_connection: TcpConnection, bypass_asyncio_connection
) -> None:
    """Test processing of program version frame."""
    test_frame = ProgramVersion(sender=ECOMAX_ADDRESS)
    test_frame_response = test_frame.response()

    with patch(
        "pyplumio.stream.FrameWriter.process_queue",
        side_effect=tcp_connection.async_close,
    ), patch("pyplumio.stream.FrameWriter.collect", return_value=True), patch(
        "pyplumio.stream.FrameReader.read",
        return_value=test_frame,
    ), patch(
        "pyplumio.frames.requests.ProgramVersion.response",
        return_value=test_frame_response,
    ) as program_version_response, patch(
        "pyplumio.stream.FrameWriter.queue"
    ) as mock_queue:
        await tcp_connection.task(AsyncMock())

    program_version_response.assert_called_once()
    mock_queue.assert_called_once_with(test_frame_response)


@pytest.mark.asyncio
async def test_process_uid_response(
    tcp_connection: TcpConnection, bypass_asyncio_connection
) -> None:
    """Test processing of uid frame."""
    product_info = ProductInfo(
        type=0, product=0, uid="test_uid", logo=0, image=0, name="test_product"
    )

    with patch(
        "pyplumio.stream.FrameWriter.process_queue",
        side_effect=tcp_connection.async_close,
    ), patch(
        "pyplumio.stream.FrameReader.read",
        return_value=UID(sender=ECOMAX_ADDRESS, data={"product": product_info}),
    ):
        await tcp_connection.task(AsyncMock())

    assert tcp_connection.devices.ecomax.uid == "test_uid"
    assert tcp_connection.devices.ecomax.product == "test_product"


@pytest.mark.asyncio
async def test_process_password_response(
    tcp_connection: TcpConnection, bypass_asyncio_connection
) -> None:
    """Test processing of password frame."""
    with patch(
        "pyplumio.stream.FrameWriter.process_queue",
        side_effect=tcp_connection.async_close,
    ), patch(
        "pyplumio.stream.FrameReader.read",
        return_value=Password(sender=ECOMAX_ADDRESS, data={"password": "0000"}),
    ):
        await tcp_connection.task(AsyncMock())

    assert tcp_connection.devices.ecomax.password == "0000"


@pytest.mark.asyncio
async def test_process_data_frame(
    tcp_connection: TcpConnection, bypass_asyncio_connection
) -> None:
    """Test processing of data frame."""
    with patch(
        "pyplumio.stream.FrameWriter.process_queue",
        side_effect=tcp_connection.async_close,
    ), patch(
        "pyplumio.stream.FrameReader.read",
        return_value=CurrentData(
            sender=ECOMAX_ADDRESS,
            data={
                "heating_temp": 60,
                "mixers": [{"temp": 50, "target": 60, "pump": False}],
            },
        ),
    ):
        await tcp_connection.task(AsyncMock())

    assert tcp_connection.devices.ecomax.heating_temp == 60
    assert tcp_connection.devices.ecomax.mixers(0).temp == 50
    assert tcp_connection.devices.ecomax.mixers(0).target == 60
    assert not tcp_connection.devices.ecomax.mixers(0).pump


@pytest.mark.asyncio
async def test_process_parameters_response(
    tcp_connection: TcpConnection, bypass_asyncio_connection
) -> None:
    """Test processing of parameters frame."""
    with patch(
        "pyplumio.stream.FrameWriter.process_queue",
        side_effect=tcp_connection.async_close,
    ), patch(
        "pyplumio.stream.FrameReader.read",
        return_value=BoilerParameters(
            sender=ECOMAX_ADDRESS, data={"summer_mode": [1, 0, 1]}
        ),
    ):
        await tcp_connection.task(AsyncMock())

    assert tcp_connection.devices.ecomax.summer_mode.min_value == 0
    assert tcp_connection.devices.ecomax.summer_mode.max_value == 1
    assert tcp_connection.devices.ecomax.summer_mode.value == 1


@pytest.mark.asyncio
async def test_process_mixer_parameters_response(
    tcp_connection: TcpConnection, bypass_asyncio_connection
) -> None:
    """Test processing of mixer parameters frame."""
    with patch(
        "pyplumio.stream.FrameWriter.process_queue",
        side_effect=tcp_connection.async_close,
    ), patch(
        "pyplumio.stream.FrameReader.read",
        return_value=MixerParameters(
            sender=ECOMAX_ADDRESS, data={"mixers": [{"mix_set_temp": [50, 30, 60]}]}
        ),
    ):
        await tcp_connection.task(AsyncMock())

    assert tcp_connection.devices.ecomax.mixers(0).mix_set_temp.min_value == 30
    assert tcp_connection.devices.ecomax.mixers(0).mix_set_temp.max_value == 60
    assert tcp_connection.devices.ecomax.mixers(0).mix_set_temp.value == 50


@pytest.mark.asyncio
async def test_process_data_schema_response(
    tcp_connection: TcpConnection, bypass_asyncio_connection
) -> None:
    """Test processing of mixer parameters frame."""
    with patch(
        "pyplumio.stream.FrameWriter.process_queue",
        side_effect=tcp_connection.async_close,
    ), patch(
        "pyplumio.stream.FrameReader.read",
        return_value=DataSchema(sender=ECOMAX_ADDRESS, data="test"),
    ):
        await tcp_connection.task(AsyncMock())

    assert tcp_connection.devices.ecomax.schema == "test"


@pytest.mark.asyncio
async def test_process_check_device_request(
    tcp_connection: TcpConnection, bypass_asyncio_connection
) -> None:
    """Test processing of check device frame."""
    # Setup test data for network information.
    eth_data: Dict[str, Any] = {
        "ip": "1.1.1.2",
        "netmask": "255.255.255.255",
        "gateway": "1.1.1.1",
    }
    wlan_data: Dict[str, Any] = {
        "ssid": "test",
        "ip": "2.2.2.2",
        "encryption": WLAN_ENCRYPTION_WPA,
        "netmask": "255.255.255.255",
        "gateway": "2.2.2.1",
        "quality": 99,
    }
    tcp_connection.set_eth(**eth_data)
    tcp_connection.set_wlan(**wlan_data)

    # Check that network information was successfully passed
    # in response to check device request.
    with patch(
        "pyplumio.stream.FrameWriter.process_queue",
        side_effect=tcp_connection.async_close,
    ), patch(
        "pyplumio.stream.FrameReader.read",
        return_value=CheckDevice(sender=ECOMAX_ADDRESS),
    ), patch(
        "pyplumio.frames.requests.CheckDevice.response"
    ) as mock_response:
        await tcp_connection.task(AsyncMock())

    mock_response.assert_called_once_with(
        data={
            "network": NetworkInfo(
                eth=EthernetParameters(**eth_data, status=True),
                wlan=WirelessParameters(**wlan_data, status=True),
            )
        }
    )
