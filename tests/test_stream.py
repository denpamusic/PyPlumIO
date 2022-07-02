"""Contains tests for frame reader and writer."""

import asyncio
from collections.abc import Generator
from unittest.mock import patch

import pytest

from pyplumio.exceptions import ChecksumError, LengthError, ReadError
from pyplumio.frames import Request
from pyplumio.frames.requests import BoilerParameters
from pyplumio.stream import FrameReader, FrameWriter


@pytest.fixture(name="frame_reader")
def fixture_frame_reader() -> Generator[FrameReader, None, None]:
    """Return instance of frame reader."""
    with patch("asyncio.StreamReader") as mock_stream_reader:
        yield FrameReader(mock_stream_reader)


@patch("asyncio.StreamWriter", autospec=True)
async def test_frame_writer(mock_stream_writer) -> None:
    """Test frame writer."""
    frame = Request(0x0)
    writer = FrameWriter(mock_stream_writer)
    await writer.write(frame)
    mock_stream_writer.write.assert_called_once_with(frame.bytes)
    mock_stream_writer.drain.assert_awaited_once()
    await writer.close()
    mock_stream_writer.close.assert_called_once()
    mock_stream_writer.wait_closed.assert_awaited_once()


async def test_frame_reader(frame_reader: FrameReader) -> None:
    """Test frame reader."""
    data: asyncio.Future = asyncio.Future()
    data.set_result(b"\x68\x0c\x00\x00\x56\x30\x05\x31\xff\x00\xc9\x16")
    with patch(
        "asyncio.StreamReader.read",
        return_value=data,
    ):
        frame = await frame_reader.read()

    assert isinstance(frame, BoilerParameters)
    assert frame.frame_type == 0x31
    assert frame.sender == 0x56
    assert frame.sender_type == 0x30
    assert frame.recipient == 0x0
    assert frame.message == b"\xff\x00"
    assert frame.econet_version == 0x5


async def test_frame_reader_with_incomplete_data(frame_reader: FrameReader) -> None:
    """Test reader with not data of less than header size in length."""
    data: asyncio.Future = asyncio.Future()
    data.set_result(b"\x68\x03\x00\x00")
    with pytest.raises(ReadError), patch(
        "asyncio.StreamReader.read",
        return_value=data,
    ):
        await frame_reader.read()


async def test_frame_reader_with_incorrect_length(frame_reader: FrameReader) -> None:
    """Test reader on frame with incorrect length."""
    data: asyncio.Future = asyncio.Future()
    data.set_result(b"\x68\x03\x00\x00\x56\x30\x05\x31\xff\x00\xc9\x16")
    with pytest.raises(LengthError), patch(
        "asyncio.StreamReader.read",
        return_value=data,
    ):
        await frame_reader.read()


async def test_frame_reader_with_incorrect_crc(frame_reader: FrameReader) -> None:
    """Test reader on frame with incorrect checksum."""
    data: asyncio.Future = asyncio.Future()
    data.set_result(b"\x68\x0c\x00\x00\x56\x30\x05\x31\xfe\x00\xc9\x16")
    with pytest.raises(ChecksumError), patch(
        "asyncio.StreamReader.read",
        return_value=data,
    ):
        await frame_reader.read()
