"""Test PyPlumIO stream reader and writer."""

from unittest.mock import Mock, patch

import pytest

from pyplumio.exceptions import ChecksumError, LengthError
from pyplumio.requests import UID, CheckDevice, Parameters, ProgramVersion
from pyplumio.stream import (
    READER_BUFFER_SIZE,
    READER_TIMEOUT,
    WRITER_TIMEOUT,
    FrameReader,
    FrameWriter,
)


@pytest.fixture(name="writer")
def fixture_writer() -> FrameWriter:
    """Return instance of frame writer."""
    mock_stream_writer = Mock()
    return FrameWriter(writer=mock_stream_writer)


@pytest.fixture(name="reader")
def fixture_reader() -> FrameReader:
    """Return instance of frame reader."""
    mock_stream_reader = Mock()
    return FrameReader(reader=mock_stream_reader)


@pytest.mark.asyncio
async def test_frame_writer(writer: FrameWriter) -> None:
    """Test frame writer."""
    # Check that writer is empty.
    writer.writer = Mock()
    assert writer.is_empty

    # Queue some requests and check that writer is not empty.
    writer.queue(ProgramVersion(), CheckDevice())
    assert not writer.is_empty
    assert len(writer) == 2

    # Check that writer has program version but not uid requests.
    assert writer.has(ProgramVersion())
    assert not writer.has(UID())

    # Add uid request and check that length is changed.
    writer.collect([UID()])
    assert len(writer) == 3
    assert writer.has(UID())

    # Iterate through requests queue and write request to stream.
    with patch(
        "asyncio.wait_for",
        return_value=True,
    ) as mock_wait_for:
        for request in (ProgramVersion(), CheckDevice(), UID()):
            await writer.process_queue()
            writer.writer.write.assert_called_once_with(request.bytes)
            writer.writer.write.reset_mock()
            mock_wait_for.assert_called_once_with(
                writer.writer.drain(), timeout=WRITER_TIMEOUT
            )
            mock_wait_for.reset_mock()

    # Check that writer queue is empty.
    assert len(writer) == 0
    assert writer.is_empty

    # Close writer and check that it is closed.
    with patch(
        "asyncio.wait_for",
        return_value=True,
    ) as mock_wait_for:
        await writer.close()

    mock_wait_for.assert_called_once_with(
        writer.writer.wait_closed(), timeout=WRITER_TIMEOUT
    )
    writer.writer.close.assert_called_once()


@pytest.mark.asyncio
async def test_frame_reader(reader: FrameReader) -> None:
    """Test frame reader."""
    with patch(
        "asyncio.wait_for",
        return_value=b"\x68\x0c\x00\x00\x56\x30\x05\x31\xff\x00\xc9\x16",
    ) as mock_wait_for:
        frame = await reader.read()
        assert isinstance(frame, Parameters)
        assert frame.type_ == 0x31
        assert frame.sender == 0x56
        assert frame.sender_type == 0x30
        assert frame.recipient == 0x0
        assert frame.message == b"\xff\x00"
        assert frame.econet_version == 0x5
        mock_wait_for.assert_called_once_with(
            reader.reader.read(READER_BUFFER_SIZE), timeout=READER_TIMEOUT
        )


@pytest.mark.asyncio
async def test_frame_reader_with_incomplete_data(reader: FrameReader) -> None:
    """Test reader with not data of less than header size in length."""
    with patch(
        "asyncio.wait_for",
        return_value=b"\x68\x03\x00\x00",
    ):
        assert await reader.read() is None


@pytest.mark.asyncio
async def test_frame_reader_with_incorrect_length(reader: FrameReader) -> None:
    """Test reader on frame with incorrect length."""
    with pytest.raises(LengthError), patch(
        "asyncio.wait_for",
        return_value=b"\x68\x03\x00\x00\x56\x30\x05\x31\xff\x00\xc9\x16",
    ):
        await reader.read()


@pytest.mark.asyncio
async def test_frame_reader_with_incorrect_crc(reader: FrameReader) -> None:
    """Test reader on frame with incorrect checksum."""
    with pytest.raises(ChecksumError), patch(
        "asyncio.wait_for",
        return_value=b"\x68\x0c\x00\x00\x56\x30\x05\x31\xfe\x00\xc9\x16",
    ):
        await reader.read()
