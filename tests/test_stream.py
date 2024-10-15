"""Contains tests for the frame reader and writer classes."""

import asyncio
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from pyplumio.const import DeviceType, FrameType
from pyplumio.exceptions import ChecksumError, ReadError, UnknownDeviceError
from pyplumio.frames import ECONET_TYPE, ECONET_VERSION
from pyplumio.frames.requests import EcomaxParametersRequest, ProgramVersionRequest
from pyplumio.stream import FrameReader, FrameWriter


@pytest.fixture(name="frame_reader")
def fixture_frame_reader() -> Generator[FrameReader, None, None]:
    """Return instance of frame reader."""
    with patch("asyncio.StreamReader") as mock_stream_reader:
        yield FrameReader(mock_stream_reader)


@pytest.fixture(name="frame_start")
def fixture_frame_start():
    """Return a read mock that contains frame start delimiter."""
    with patch(
        "asyncio.StreamReader.read", return_value=b"\x68", new_callable=AsyncMock
    ):
        yield


@patch("asyncio.StreamWriter", autospec=True)
async def test_frame_writer(mock_stream_writer) -> None:
    """Test frame writer."""
    frame = ProgramVersionRequest()
    writer = FrameWriter(mock_stream_writer)
    await writer.write(frame)
    mock_stream_writer.write.assert_called_once_with(frame.bytes)
    mock_stream_writer.drain.assert_awaited_once()
    await writer.close()
    mock_stream_writer.close.assert_called_once()
    mock_stream_writer.wait_closed.assert_awaited_once()


@pytest.mark.parametrize(
    ("method", "exception"), [("close", OSError), ("wait_closed", asyncio.TimeoutError)]
)
@patch("asyncio.StreamWriter", autospec=True)
async def test_frame_writer_with_close_error(
    mock_stream_writer, method, exception, caplog
) -> None:
    """Test frame writer with error on writer close."""
    writer = FrameWriter(mock_stream_writer)
    getattr(mock_stream_writer, method).side_effect = exception
    await writer.close()
    assert "Unexpected error, while closing the writer" in caplog.text


@patch(
    "asyncio.StreamReader.read", side_effect=(b"\x00", b"\x68"), new_callable=AsyncMock
)
@patch(
    "asyncio.StreamReader.readexactly",
    side_effect=(b"\x0c\x00\x00\x56\x30\x05", b"\x31\xff\x00\xc9\x16"),
    new_callable=AsyncMock,
)
async def test_frame_reader(
    mock_read, mock_readexactly, frame_reader: FrameReader
) -> None:
    """Test frame reader."""
    frame = await frame_reader.read()
    assert isinstance(frame, EcomaxParametersRequest)
    assert frame.frame_type == FrameType.REQUEST_ECOMAX_PARAMETERS
    assert frame.sender == DeviceType.ECONET
    assert frame.econet_type == ECONET_TYPE
    assert frame.recipient == DeviceType.ALL
    assert frame.message == b"\xff\x00"
    assert frame.econet_version == ECONET_VERSION
    assert mock_read.call_count == 2
    assert mock_readexactly.call_count == 2


@patch("asyncio.StreamReader.read", return_value=False, new_callable=AsyncMock)
async def test_frame_reader_with_empty_buffer(
    mock_read, frame_reader: FrameReader
) -> None:
    """Test reader with empty read buffer."""
    with pytest.raises(OSError) as exc_info:
        await frame_reader.read()

    assert "Serial connection broken" in str(exc_info.value)
    mock_read.assert_awaited_once()


@patch(
    "asyncio.StreamReader.readexactly",
    side_effect=asyncio.IncompleteReadError(bytearray(), expected=7),
    new_callable=AsyncMock,
)
async def test_frame_reader_with_short_header(
    mock_readexactly, frame_reader: FrameReader, frame_start
) -> None:
    """Test reader when data is less than header size."""
    with pytest.raises(ReadError) as exc_info:
        await frame_reader.read()

    assert "Got incomplete header, while trying to read 7 bytes" in str(exc_info.value)


@patch(
    "asyncio.StreamReader.readexactly",
    side_effect=(b"\x03\x00\x00\x56\x30\x05", b"\x31\xff\x00\xc9\x16"),
    new_callable=AsyncMock,
)
async def test_frame_reader_with_incorrect_length(
    mock_readexactly, frame_reader: FrameReader, frame_start
) -> None:
    """Test reader on frame with incorrect length."""
    with pytest.raises(ReadError) as exc_info:
        await frame_reader.read()

    assert "Unexpected frame length (3)" in str(exc_info.value)


@patch(
    "asyncio.StreamReader.readexactly",
    side_effect=(
        b"\x0c\x00\x00\x56\x30\x05",
        asyncio.IncompleteReadError(bytearray(), 10),
    ),
    new_callable=AsyncMock,
)
async def test_frame_reader_with_incomplete_read(
    mock_readexactly, frame_reader: FrameReader, frame_start
) -> None:
    """Test reader with incomplete data."""
    with pytest.raises(ReadError) as exc_info:
        await frame_reader.read()

    assert "Got incomplete frame, while trying to read 10 bytes" in str(exc_info.value)


@patch(
    "asyncio.StreamReader.readexactly",
    side_effect=(b"\x0c\x00\x00\x56\x30\x05", b"\x31\xfe\x00\xc9\x16"),
    new_callable=AsyncMock,
)
async def test_frame_reader_with_incorrect_bcc(
    mock_readexactly, frame_reader: FrameReader, frame_start
) -> None:
    """Test reader on frame with incorrect checksum."""
    with pytest.raises(ChecksumError) as exc_info:
        await frame_reader.read()

    assert "Incorrect frame checksum (200 != 201)" in str(exc_info.value)


@patch(
    "asyncio.StreamReader.readexactly",
    side_effect=(b"\x0c\x00\x10\x56\x30\x05", b"\x31\xff\x00\xc9\x16"),
    new_callable=AsyncMock,
)
async def test_frame_reader_with_unknown_recipient(
    mock_readexactly, frame_reader: FrameReader, frame_start
) -> None:
    """Test reader on frame with unknown recipient address."""
    result = await frame_reader.read()
    assert result is None


@patch(
    "asyncio.StreamReader.readexactly",
    side_effect=(b"\x0c\x00\x00\x10\x30\x05", b"\x31\xff\x00\xc9\x16"),
    new_callable=AsyncMock,
)
async def test_frame_reader_with_unknown_sender(
    mock_readexactly, frame_reader: FrameReader, frame_start
) -> None:
    """Test reader on frame with unknown sender address."""
    with pytest.raises(UnknownDeviceError) as exc_info:
        await frame_reader.read()

    assert "Unknown sender type (16)" in str(exc_info.value)
