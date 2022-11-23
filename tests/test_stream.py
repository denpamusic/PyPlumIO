"""Contains tests for frame reader and writer."""

import asyncio
from typing import Generator
from unittest.mock import AsyncMock, patch

import pytest

from pyplumio.exceptions import ChecksumError, ReadError
from pyplumio.frames.requests import EcomaxParametersRequest, ProgramVersionRequest
from pyplumio.stream import FrameReader, FrameWriter


@pytest.fixture(name="frame_reader")
def fixture_frame_reader() -> Generator[FrameReader, None, None]:
    """Return instance of frame reader."""
    with patch("asyncio.StreamReader") as mock_stream_reader:
        yield FrameReader(mock_stream_reader)


@patch("asyncio.StreamWriter", autospec=True)
async def test_frame_writer(mock_stream_writer, bypass_asyncio_sleep) -> None:
    """Test frame writer."""
    frame = ProgramVersionRequest
    writer = FrameWriter(mock_stream_writer)
    await writer.write(frame)
    mock_stream_writer.write.assert_called_once_with(frame.bytes)
    mock_stream_writer.drain.assert_awaited_once()
    await writer.close()
    mock_stream_writer.close.assert_called_once()
    mock_stream_writer.wait_closed.assert_awaited_once()


@patch(
    "asyncio.StreamReader.read",
    side_effect=(b"\x00", b"\x68", b"\x0c\x00\x00\x56\x30\x05"),
    new_callable=AsyncMock,
)
@patch(
    "asyncio.StreamReader.readexactly",
    return_value=b"\x31\xff\x00\xc9\x16",
    new_callable=AsyncMock,
)
async def test_frame_reader(
    mock_readexactly, mock_read, frame_reader: FrameReader
) -> None:
    """Test frame reader."""
    frame = await frame_reader.read()
    assert isinstance(frame, EcomaxParametersRequest)
    assert frame.frame_type == 0x31
    assert frame.sender == 0x56
    assert frame.sender_type == 0x30
    assert frame.recipient == 0x0
    assert frame.message == b"\xff\x00"
    assert frame.econet_version == 0x5
    assert mock_read.call_count == 3
    assert mock_readexactly.call_count == 1


@patch(
    "asyncio.StreamReader.read",
    return_value=False,
    new_callable=AsyncMock,
)
async def test_frame_reader_with_empty_buffer(
    mock_read, frame_reader: FrameReader
) -> None:
    """Test reader with empty read buffer."""
    with pytest.raises(OSError):
        await frame_reader.read()

    mock_read.assert_awaited_once()


@patch(
    "asyncio.StreamReader.read",
    side_effect=(b"\x68", b"\x03\x00\x00"),
    new_callable=AsyncMock,
)
async def test_frame_reader_with_short_header(
    mock_read, frame_reader: FrameReader
) -> None:
    """Test reader when data is less than header size."""
    with pytest.raises(ReadError):
        await frame_reader.read()

    assert mock_read.call_count == 2


@patch(
    "asyncio.StreamReader.read",
    side_effect=(b"\x68", b"\x03\x00\x00\x56\x30\x05"),
    new_callable=AsyncMock,
)
@patch(
    "asyncio.StreamReader.readexactly",
    return_value=b"\x31\xff\x00\xc9\x16",
    new_callable=AsyncMock,
)
async def test_frame_reader_with_incorrect_length(
    mock_readexactly, mock_read, frame_reader: FrameReader
) -> None:
    """Test reader on frame with incorrect length."""
    with pytest.raises(ReadError):
        await frame_reader.read()


@patch(
    "asyncio.StreamReader.read",
    side_effect=(b"\x68", b"\x0c\x00\x00\x56\x30\x05"),
    new_callable=AsyncMock,
)
@patch(
    "asyncio.StreamReader.readexactly",
    side_effect=asyncio.IncompleteReadError(bytearray(), None),
    new_callable=AsyncMock,
)
async def test_frame_reader_with_incomplete_read(
    mock_readexactly, mock_read, frame_reader: FrameReader
) -> None:
    """Test reader with incomplete data."""
    with pytest.raises(ReadError):
        await frame_reader.read()


@patch(
    "asyncio.StreamReader.read",
    side_effect=(b"\x68", b"\x0c\x00\x00\x56\x30\x05"),
    new_callable=AsyncMock,
)
@patch(
    "asyncio.StreamReader.readexactly",
    return_value=b"\x31\xfe\x00\xc9\x16",
    new_callable=AsyncMock,
)
async def test_frame_reader_with_incorrect_crc(
    mock_readexactly, mock_read, frame_reader: FrameReader
) -> None:
    """Test reader on frame with incorrect checksum."""
    with pytest.raises(ChecksumError):
        await frame_reader.read()


@patch(
    "asyncio.StreamReader.read",
    side_effect=(b"\x68", b"\x0c\x00\x10\x56\x30\x05"),
    new_callable=AsyncMock,
)
@patch(
    "asyncio.StreamReader.readexactly",
    return_value=b"\x31\xff\x00\xc9\x16",
    new_callable=AsyncMock,
)
async def test_frame_reader_with_unknown_address(
    mock_readexactly, mock_read, frame_reader: FrameReader
) -> None:
    """Test reader on frame with unknown device address."""
    result = await frame_reader.read()
    assert result is None
