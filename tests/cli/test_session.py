"""Contains tests for the CLI session module."""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from serialx import SerialException

import pyplumio
from pyplumio.cli.session import SERVICE_PARAMETERS_REQUEST, UID_REQUEST, Session
from pyplumio.connection import RECONNECT_AFTER_SECONDS
from pyplumio.const import DeviceType, ProductType
from pyplumio.exceptions import (
    ChecksumError,
    ConnectionFailedError,
    FrameDataError,
    PyPlumIOError,
    ReadError,
    UnknownDeviceError,
    UnknownFrameError,
)
from pyplumio.frames import responses
from pyplumio.parameters import ParameterValues
from pyplumio.structures.ecomax_service_parameters import ATTR_ECOMAX_SERVICE_PARAMETERS
from pyplumio.structures.product_info import ATTR_PRODUCT, ProductInfo


@pytest.fixture
def product_info() -> ProductInfo:
    """Return sample product info."""
    return ProductInfo(
        type=ProductType.ECOMAX_P,
        id=90,
        uid="*TEST*",
        logo=0,
        image=0,
        model="ecoMAX 350P2-ZF",
    )


@pytest.fixture
def mock_connection() -> AsyncMock:
    """Return a mock connection with connected event."""
    connection = AsyncMock()
    connection.connected = asyncio.Event()
    connection.connected.set()
    connection.reader = AsyncMock()
    connection.writer = AsyncMock()
    return connection


@pytest.fixture
def service_parameters_response() -> responses.EcomaxServiceParametersResponse:
    """Return sample service parameters response."""
    return responses.EcomaxServiceParametersResponse(
        recipient=DeviceType.ECONET,
        sender=DeviceType.ECOMAX,
        message=b"\x01\x02\x03",
        data={
            ATTR_ECOMAX_SERVICE_PARAMETERS: [
                (0, ParameterValues(value=50, min_value=0, max_value=100))
            ]
        },
    )


async def test_session_connect_success(
    product_info: ProductInfo,
    mock_connection: AsyncMock,
    service_parameters_response: responses.EcomaxServiceParametersResponse,
) -> None:
    """Test successful session connection and parameter retrieval."""
    uid_response = responses.UIDResponse(
        recipient=DeviceType.ECONET,
        sender=DeviceType.ECOMAX,
        data={ATTR_PRODUCT: product_info},
    )
    mock_connection.reader.read.side_effect = [
        uid_response,
        service_parameters_response,
        asyncio.CancelledError(),
    ]

    on_update = MagicMock()
    on_status = MagicMock()
    session = Session(
        url="socket://localhost:8899",
        baudrate=115200,
        interval=1.0,
        on_update=on_update,
        on_status=on_status,
    )

    with patch("pyplumio.serial_for_url", return_value=mock_connection):
        info = await session.connect(retries=2, timeout=1.0)
        assert info == product_info
        assert session.product_info == product_info
        assert session.url == "socket://localhost:8899"
        assert session.baudrate == 115200
        assert bool(session.connected)
        assert session.last_frame_message == b"\x01\x02\x03"

        on_update.assert_called_once_with(
            [(0, ParameterValues(value=50, min_value=0, max_value=100))]
        )
        assert on_status.call_args_list == [
            call("Connecting to socket://localhost:8899..."),
            call("Requesting product info (1/2)..."),
            call("Requesting service parameters for ecoMAX 350P2-ZF (1/2)..."),
            call("Received 1 service parameters."),
        ]

        await session.close()
        assert not session.connected
        mock_connection.close.assert_awaited_once()


async def test_session_connect_retry_and_timeout(
    product_info: ProductInfo,
    mock_connection: AsyncMock,
    service_parameters_response: responses.EcomaxServiceParametersResponse,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test session connection retry on timeout and eventual success."""
    uid_response = responses.UIDResponse(
        recipient=DeviceType.ECONET,
        sender=DeviceType.ECOMAX,
        data={ATTR_PRODUCT: product_info},
    )

    mock_connection.reader.read.side_effect = [
        TimeoutError(),
        uid_response,
        TimeoutError(),
        service_parameters_response,
        asyncio.CancelledError(),
    ]

    on_status = MagicMock()
    with patch("pyplumio.serial_for_url", return_value=mock_connection):
        session = Session(url="/dev/ttyUSB0", on_status=on_status)
        info = await session.connect(retries=2, timeout=1.0)
        assert info == product_info
        assert on_status.call_args_list == [
            call("Connecting to /dev/ttyUSB0..."),
            call("Requesting product info (1/2)..."),
            call("Requesting product info (2/2)..."),
            call("Requesting service parameters for ecoMAX 350P2-ZF (1/2)..."),
            call("Requesting service parameters for ecoMAX 350P2-ZF (2/2)..."),
            call("Received 1 service parameters."),
        ]
        assert "Product info attempt 1/2 timed out" in caplog.text
        assert "Service parameters attempt 1/2 timed out" in caplog.text
        await session.close()


async def test_session_connect_service_parameters_unsupported(
    product_info: ProductInfo, mock_connection: AsyncMock
) -> None:
    """Test session connection failure when service parameters unsupported."""
    uid_response = responses.UIDResponse(
        recipient=DeviceType.ECONET,
        sender=DeviceType.ECOMAX,
        data={ATTR_PRODUCT: product_info},
    )

    mock_connection.reader.read.side_effect = [
        uid_response,
        TimeoutError(),
        TimeoutError(),
    ]

    with patch("pyplumio.serial_for_url", return_value=mock_connection):
        session = Session(url="/dev/ttyUSB0")
        with pytest.raises(
            PyPlumIOError,
            match=(
                "ecoMAX 350P2-ZF did not return service parameters after 2 attempts; "
                "this controller may not support them"
            ),
        ):
            await session.connect(retries=2, timeout=0.1)
        await session.close()

    empty_params_response = responses.EcomaxServiceParametersResponse(
        recipient=DeviceType.ECONET,
        sender=DeviceType.ECOMAX,
        message=b"",
        data={ATTR_ECOMAX_SERVICE_PARAMETERS: []},
    )
    mock_connection.reader.read.side_effect = [
        uid_response,
        empty_params_response,
        TimeoutError(),
        empty_params_response,
        TimeoutError(),
    ]

    with patch("pyplumio.serial_for_url", return_value=mock_connection):
        session = Session(url="/dev/ttyUSB0")
        with pytest.raises(
            PyPlumIOError,
            match=(
                "ecoMAX 350P2-ZF did not return service parameters after 2 attempts; "
                "this controller may not support them"
            ),
        ):
            await session.connect(retries=2, timeout=0.1)
        await session.close()


async def test_session_product_info_connection_lost(
    mock_connection: AsyncMock,
) -> None:
    """Test disconnect during product info retrieval raises immediately."""

    def drop_and_timeout() -> None:
        mock_connection.connected.clear()
        raise TimeoutError

    mock_connection.reader.read.side_effect = drop_and_timeout

    with patch("pyplumio.serial_for_url", return_value=mock_connection):
        session = Session(url="socket://localhost:8899")
        with pytest.raises(
            PyPlumIOError, match="Connection lost while requesting product info"
        ):
            await session.connect(retries=3, timeout=0.1)

        assert mock_connection.writer.write.await_count == 1
        await session.close()


async def test_session_service_parameters_connection_lost(
    product_info: ProductInfo, mock_connection: AsyncMock
) -> None:
    """Test disconnect during service parameters retrieval raises immediately."""
    uid_response = responses.UIDResponse(
        recipient=DeviceType.ECONET,
        sender=DeviceType.ECOMAX,
        data={ATTR_PRODUCT: product_info},
    )
    calls = 0

    def read_or_drop() -> responses.UIDResponse:
        nonlocal calls
        calls += 1
        if calls == 1:
            return uid_response

        mock_connection.connected.clear()
        raise TimeoutError

    mock_connection.reader.read.side_effect = read_or_drop

    with patch("pyplumio.serial_for_url", return_value=mock_connection):
        session = Session(url="socket://localhost:8899")
        with pytest.raises(
            PyPlumIOError,
            match="Connection lost while requesting service parameters",
        ):
            await session.connect(retries=3, timeout=0.1)

        assert mock_connection.writer.write.await_count == 2
        await session.close()


async def test_session_connect_failure(mock_connection: AsyncMock) -> None:
    """Test session connection failure after retries exhausted."""
    mock_connection.reader.read.side_effect = TimeoutError()

    with patch("pyplumio.serial_for_url", return_value=mock_connection):
        session = Session(url="/dev/ttyUSB0")
        with pytest.raises(PyPlumIOError, match="Failed to retrieve product info"):
            await session.connect(retries=2, timeout=0.1)
        await session.close()


async def test_session_read_until_product_info_and_protocol_error(
    product_info: ProductInfo, mock_connection: AsyncMock
) -> None:
    """Test _read_until with _extract_product_info skips ProtocolError."""
    uid_response = responses.UIDResponse(
        recipient=DeviceType.ECONET,
        sender=DeviceType.ECOMAX,
        data={ATTR_PRODUCT: product_info},
    )

    mock_connection.reader.read.side_effect = [
        pyplumio.ProtocolError("corrupt frame"),
        responses.ProgramVersionResponse(),
        uid_response,
    ]

    session = Session(url="socket://localhost:8899")
    session._connection = mock_connection
    info = await session._read_until(session._extract_product_info, timeout=2.0)
    assert info == product_info

    mock_connection.reader.read.side_effect = [responses.ProgramVersionResponse()]
    assert (
        await session._request_with_retries(
            UID_REQUEST,
            lambda _frame: 0,
            label="zero result",
            error_message="unused",
            retries=1,
            timeout=1.0,
        )
        == 0
    )

    mock_connection.connected.clear()
    assert await session._read_until(session._extract_product_info, timeout=1.0) is None

    with pytest.raises(PyPlumIOError, match="Connection lost while requesting"):
        await session._request_with_retries(
            UID_REQUEST,
            session._extract_product_info,
            label="product info",
            error_message="Failed to retrieve product info",
            retries=1,
            timeout=1.0,
        )


async def test_session_read_until_service_parameters_and_protocol_error(
    mock_connection: AsyncMock,
    service_parameters_response: responses.EcomaxServiceParametersResponse,
) -> None:
    """Test _read_until with _extract_service_parameters and disconnects."""
    mock_connection.reader.read.side_effect = [
        pyplumio.ProtocolError("corrupt frame"),
        responses.ProgramVersionResponse(),
        None,
        service_parameters_response,
    ]
    session = Session(url="socket://localhost:8899")
    session._connection = mock_connection

    parameters = await session._read_until(
        session._extract_service_parameters, timeout=2.0
    )
    assert (
        parameters == service_parameters_response.data[ATTR_ECOMAX_SERVICE_PARAMETERS]
    )

    mock_connection.connected.clear()
    assert (
        await session._read_until(session._extract_service_parameters, timeout=1.0)
        is None
    )

    mock_connection.connected.set()
    session._connection = None
    assert (
        await session._read_until(session._extract_service_parameters, timeout=1.0)
        is None
    )

    session._connection = mock_connection
    mock_connection.reader.read.side_effect = TimeoutError()
    with pytest.raises(PyPlumIOError, match="custom failure"):
        await session._request_with_retries(
            SERVICE_PARAMETERS_REQUEST,
            session._extract_service_parameters,
            label="service parameters",
            error_message="custom failure",
            retries=1,
            timeout=0.1,
        )


async def test_session_frames_and_polling(mock_connection: AsyncMock) -> None:
    """Test receiving parameters and frame handling."""
    param_values = ParameterValues(value=50, min_value=0, max_value=100)
    params_response = responses.EcomaxServiceParametersResponse(
        recipient=DeviceType.ECONET,
        sender=DeviceType.ECOMAX,
        message=b"\x01\x02\x03",
        data={ATTR_ECOMAX_SERVICE_PARAMETERS: [(0, param_values)]},
    )

    on_update = MagicMock()
    session = Session(url="socket://localhost:8899", interval=0.1, on_update=on_update)
    session._connection = mock_connection

    assert session._extract_service_parameters(params_response) == [(0, param_values)]
    assert session.last_frame_message == b"\x01\x02\x03"
    assert session.last_parameters == [(0, param_values)]
    assert session.last_update_time is not None
    on_update.assert_called_once_with([(0, param_values)])

    assert (
        session._extract_service_parameters(responses.ProgramVersionResponse()) is None
    )

    async def dummy() -> None:
        await asyncio.Event().wait()

    session.create_task(dummy())
    await session.close()


async def test_session_read_oserror_disconnect(mock_connection: AsyncMock) -> None:
    """Test _read_loop stopping and notifying on OSError."""
    mock_connection.reader.read.side_effect = OSError("Connection reset by peer")

    session = Session(url="socket://localhost:8899")
    session._connection = mock_connection

    await session._read_loop()
    mock_connection.connection_lost.assert_awaited_once()


async def test_session_read_readerror_disconnect(mock_connection: AsyncMock) -> None:
    """Test _read_loop stopping and notifying on ReadError."""
    mock_connection.reader.read.side_effect = ReadError("Incomplete frame read")

    session = Session(url="socket://localhost:8899")
    session._connection = mock_connection

    await session._read_loop()
    mock_connection.connection_lost.assert_awaited_once()


async def test_session_read_timeouterror_disconnect(mock_connection: AsyncMock) -> None:
    """Test _read_loop stopping and notifying on TimeoutError."""
    mock_connection.reader.read.side_effect = TimeoutError()

    session = Session(url="socket://localhost:8899")
    session._connection = mock_connection

    await session._read_loop()
    mock_connection.connection_lost.assert_awaited_once()


async def test_session_write_oserror_disconnect_and_sleep(
    skip_asyncio_sleep: AsyncMock, mock_connection: AsyncMock
) -> None:
    """Test _poll_loop sleeping after write and notifying disconnect on error."""
    mock_connection.writer.write.side_effect = [None, OSError("Broken pipe")]

    session = Session(url="socket://localhost:8899", interval=1.5)
    session._connection = mock_connection

    await session._poll_loop()
    mock_connection.connection_lost.assert_awaited_once()
    skip_asyncio_sleep.assert_called_once_with(1.5)


async def test_session_read_recoverable_errors_skipped(
    mock_connection: AsyncMock,
) -> None:
    """Test _read_loop skips recoverable protocol errors and propagates cancellation."""
    param_values = ParameterValues(value=10, min_value=0, max_value=20)
    valid_response = responses.EcomaxServiceParametersResponse(
        recipient=DeviceType.ECONET,
        sender=DeviceType.ECOMAX,
        message=b"\xaa\xbb",
        data={ATTR_ECOMAX_SERVICE_PARAMETERS: [(1, param_values)]},
    )

    mock_connection.reader.read.side_effect = [
        ChecksumError("bad checksum"),
        UnknownDeviceError("unknown device"),
        UnknownFrameError("unknown frame"),
        FrameDataError("bad data"),
        valid_response,
        asyncio.CancelledError(),
    ]

    session = Session(url="socket://localhost:8899")
    session._connection = mock_connection

    with pytest.raises(asyncio.CancelledError):
        await session._read_loop()

    assert session.last_frame_message == b"\xaa\xbb"
    assert session.last_parameters == [(1, param_values)]


async def test_session_poll_cancellation_propagating(
    mock_connection: AsyncMock,
) -> None:
    """Test _poll_loop propagates CancelledError."""
    mock_connection.writer.write.side_effect = asyncio.CancelledError()

    session = Session(url="socket://localhost:8899")
    session._connection = mock_connection

    with pytest.raises(asyncio.CancelledError):
        await session._poll_loop()


async def test_session_handle_disconnect(
    mock_connection: AsyncMock, caplog: pytest.LogCaptureFixture
) -> None:
    """Test _handle_disconnect cancels tasks, logs error, and schedules reconnect."""
    session = Session(url="socket://localhost:8899")
    session._connection = mock_connection

    async def dummy() -> None:
        await asyncio.Event().wait()

    task1 = session.create_task(dummy())

    with patch.object(Session, "_reconnect", new_callable=AsyncMock) as mock_reconnect:
        await session._handle_disconnect()
        assert task1.cancelling() or task1.cancelled()
        assert "Connection lost. Reconnecting in background..." in caplog.text
        await session.wait_until_done()
        mock_reconnect.assert_awaited_once()


async def test_session_reconnect_loop(
    skip_asyncio_sleep: AsyncMock,
    mock_connection: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test _reconnect retries after ConnectionFailedError and SerialException."""
    session = Session(url="socket://localhost:8899")
    session._connection = mock_connection
    session.last_frame_message = b"\x01"
    attempts = 0

    async def fake_connect() -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ConnectionFailedError

        if attempts == 2:
            raise SerialException("port busy")

        mock_connection.connected.set()

    mock_connection.connect.side_effect = fake_connect
    mock_connection.connected.clear()
    mock_connection.writer.write.side_effect = asyncio.CancelledError()
    mock_connection.reader.read.side_effect = asyncio.CancelledError()

    with caplog.at_level(logging.WARNING):
        await session._handle_disconnect()
        await session.wait_until_done()

    assert mock_connection.connect.await_count == 3
    skip_asyncio_sleep.assert_has_calls([call(RECONNECT_AFTER_SECONDS)] * 3)
    mock_connection.writer.write.assert_awaited_once()
    mock_connection.reader.read.assert_awaited_once()
    assert any(
        record.levelno == logging.WARNING and record.message == "Connection restored."
        for record in caplog.records
    )
