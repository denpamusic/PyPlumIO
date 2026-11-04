"""Contains tests for the CLI session module."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import pyplumio
from pyplumio.cli.session import Session
from pyplumio.const import DeviceType, ProductType
from pyplumio.exceptions import PyPlumIOError
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


async def test_session_connect_success(product_info: ProductInfo) -> None:
    """Test successful session connection and UID retrieval."""
    mock_connection = AsyncMock()
    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    mock_connection.reader = mock_reader
    mock_connection.writer = mock_writer

    uid_response = responses.UIDResponse(
        recipient=DeviceType.ECONET,
        sender=DeviceType.ECOMAX,
        data={ATTR_PRODUCT: product_info},
    )
    mock_reader.read.side_effect = [uid_response, asyncio.CancelledError()]

    on_update = MagicMock()
    session = Session(
        url="socket://localhost:8899",
        baudrate=115200,
        interval=1.0,
        on_update=on_update,
    )

    with patch("pyplumio.serial_for_url", return_value=mock_connection):
        info = await session.connect(retries=2, timeout=1.0)
        assert info == product_info
        assert session.product_info == product_info
        assert session.url == "socket://localhost:8899"
        assert session.baudrate == 115200

        # Close session
        await session.close()
        mock_connection.close.assert_awaited_once()


async def test_session_connect_retry_and_timeout(
    product_info: ProductInfo,
) -> None:
    """Test session connection retry on timeout and eventual success."""
    mock_connection = AsyncMock()
    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    mock_connection.reader = mock_reader
    mock_connection.writer = mock_writer

    uid_response = responses.UIDResponse(
        recipient=DeviceType.ECONET,
        sender=DeviceType.ECOMAX,
        data={ATTR_PRODUCT: product_info},
    )

    mock_reader.read.side_effect = [
        TimeoutError(),
        uid_response,
        asyncio.CancelledError(),
    ]

    with patch("pyplumio.serial_for_url", return_value=mock_connection):
        session = Session(url="/dev/ttyUSB0")
        info = await session.connect(retries=2, timeout=1.0)
        assert info == product_info
        await session.close()


async def test_session_connect_failure() -> None:
    """Test session connection failure after retries exhausted."""
    mock_connection = AsyncMock()
    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    mock_connection.reader = mock_reader
    mock_connection.writer = mock_writer
    mock_reader.read.side_effect = TimeoutError()

    with patch("pyplumio.serial_for_url", return_value=mock_connection):
        session = Session(url="/dev/ttyUSB0")
        with pytest.raises(PyPlumIOError, match="Failed to retrieve product info"):
            await session.connect(retries=2, timeout=0.1)
        await session.close()


async def test_session_read_uid_protocol_error(product_info: ProductInfo) -> None:
    """Test _read_uid handles and skips ProtocolError."""
    mock_connection = AsyncMock()
    mock_reader = AsyncMock()
    mock_connection.reader = mock_reader
    uid_response = responses.UIDResponse(
        recipient=DeviceType.ECONET,
        sender=DeviceType.ECOMAX,
        data={ATTR_PRODUCT: product_info},
    )

    mock_reader.read.side_effect = [
        pyplumio.ProtocolError("corrupt frame"),
        uid_response,
    ]

    session = Session(url="socket://localhost:8899")
    session._connection = mock_connection
    info = await session._read_uid(timeout=2.0)
    assert info == product_info

    # Test read_uid timeout expired returns None
    session._connection = mock_connection
    assert await session._read_uid(timeout=0) is None

    # Test read_uid when not connected
    session._connection = None
    assert await session._read_uid(timeout=1.0) is None

    # Test _fetch_product_info when disconnected
    with pytest.raises(PyPlumIOError, match="Failed to retrieve product info"):
        await session._fetch_product_info(retries=1, timeout=1.0)


async def test_session_frames_and_polling() -> None:
    """Test receiving parameters and sending poll requests."""
    mock_connection = AsyncMock()
    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    mock_connection.reader = mock_reader
    mock_connection.writer = mock_writer

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

    # Test _handle_frame
    session._handle_frame(params_response)
    assert session.last_frame_message == b"\x01\x02\x03"
    assert session.last_parameters == [(0, param_values)]
    assert session.last_update_time is not None
    on_update.assert_called_once_with([(0, param_values)], b"\x01\x02\x03")

    # Test _handle_frame ignoring irrelevant frames
    session._handle_frame(responses.ProgramVersionResponse())

    # Test _poll_loop normal iteration, exception handling, and cancellation
    mock_writer.write.side_effect = [
        None,
        Exception("write error"),
        asyncio.CancelledError(),
    ]
    await session._poll_loop()

    # Test _read_loop normal frame, ProtocolError, exception, and cancellation
    mock_reader.read.side_effect = [
        params_response,
        pyplumio.ProtocolError("ignore"),
        Exception("read error"),
        asyncio.CancelledError(),
    ]
    await session._read_loop()

    # Test close with active background task
    async def dummy() -> None:
        await asyncio.Event().wait()

    session._tasks.add(asyncio.create_task(dummy()))
    await session.close()
