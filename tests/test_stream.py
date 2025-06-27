"""Contains tests for the frame reader and writer classes."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
import logging
from unittest.mock import AsyncMock, call, patch

import pytest

from pyplumio.const import DeviceType, FrameType
from pyplumio.exceptions import ChecksumError, ReadError, UnknownDeviceError
from pyplumio.frames import ECONET_TYPE, ECONET_VERSION
from pyplumio.frames.requests import EcomaxParametersRequest, ProgramVersionRequest
from pyplumio.stream import (
    DEFAULT_BUFFER_SIZE,
    MAX_FRAME_LENGTH,
    WRITER_TIMEOUT,
    BufferManager,
    FrameReader,
    FrameWriter,
)


@pytest.fixture(name="mock_stream_writer")
def fixture_mock_stream_writer() -> Generator[asyncio.StreamWriter, None, None]:
    """Mock asyncio StreamWriter.

    Provides a patched StreamWriter for testing purposes.
    """
    with patch("asyncio.StreamWriter", autospec=True) as mock_stream_writer:
        yield mock_stream_writer


@pytest.fixture(name="frame_writer")
def fixture_frame_writer(mock_stream_writer) -> FrameWriter:
    """FrameWriter instance.

    Returns a FrameWriter using the mocked StreamWriter.
    """
    return FrameWriter(mock_stream_writer)


@pytest.fixture(name="buffer_manager")
def fixture_buffer_manager() -> Generator[BufferManager]:
    """BufferManager instance.

    Returns a BufferManager using a patched StreamReader.
    """
    with patch("asyncio.StreamReader", autospec=True) as mock_stream_reader:
        yield BufferManager(mock_stream_reader)


@pytest.fixture(name="frame_reader")
def fixture_frame_reader() -> Generator[FrameReader]:
    """FrameReader instance.

    Returns a FrameReader using a patched StreamReader.
    """
    with patch("asyncio.StreamReader", autospec=True) as mock_stream_reader:
        yield FrameReader(mock_stream_reader)


@pytest.fixture(name="read_frame_start")
def fixture_read_frame_start():
    """Mock frame start delimiter.

    Patches StreamReader.read to return the frame start byte.
    """
    with patch("asyncio.StreamReader.read", return_value=b"\x68") as mock_read:
        yield mock_read


class TestFrameWriter:
    """Tests for FrameWriter class.

    Verifies writing, closing, and waiting for close operations.
    """

    async def test_write(self, frame_writer: FrameWriter, mock_stream_writer) -> None:
        """Test writing.

        Ensures FrameWriter writes and drains as expected.
        """
        program_version_request = ProgramVersionRequest()
        await frame_writer.write(program_version_request)
        mock_stream_writer.write.assert_called_once_with(program_version_request.bytes)
        mock_stream_writer.drain.assert_awaited_once()

    @pytest.mark.parametrize(
        ("expect_exception", "exception"),
        [
            (False, None),
            (True, OSError),
            (True, asyncio.TimeoutError),
        ],
    )
    async def test_close(
        self,
        expect_exception: bool,
        exception: type[Exception],
        frame_writer: FrameWriter,
        mock_stream_writer,
        caplog,
    ) -> None:
        """Test closing.

        Checks FrameWriter.close handles exceptions and logs errors.
        """
        if expect_exception:
            mock_stream_writer.close.side_effect = exception

        await frame_writer.close()
        if expect_exception:
            assert (
                "Failed to close the frame writer due to an unexpected error"
                in caplog.text
            )
        else:
            mock_stream_writer.close.assert_called_once()
            mock_stream_writer.wait_closed.assert_awaited_once()

    async def test_wait_closed(
        self, frame_writer: FrameWriter, mock_stream_writer
    ) -> None:
        """Test wait_closed.

        Ensures wait_closed awaits the writer and checks timeout.
        """
        await frame_writer.wait_closed()
        mock_stream_writer.wait_closed.assert_awaited_once()

        # Check for timeout decorator presence and value.
        assert (
            getattr(FrameWriter.wait_closed, "_has_timeout_seconds", None)
            == WRITER_TIMEOUT
        )


class TestBufferManager:
    """Test for BufferManager class.

    Verifies handling of internal buffer.
    """

    @patch("pyplumio.stream.BufferManager.trim_to")
    @patch("asyncio.StreamReader.readexactly")
    @pytest.mark.parametrize(
        ("size", "data"),
        (
            (0, bytearray()),
            (3, bytearray(b"\x00\x01\x02")),
            (5, bytearray(b"\x00\x01\x02\x03\x04")),
        ),
    )
    async def test_ensure_buffer(
        self,
        mock_readexactly,
        mock_trim_to,
        buffer_manager: BufferManager,
        size: int,
        data: bytearray,
    ) -> None:
        """Test ensuring buffer size.

        Ensures that the buffer is filled to the requested size and
        that the buffer is trimmed appropriately.
        """
        mock_readexactly.return_value = data
        await buffer_manager.ensure_buffer(size)
        if size == 0:
            mock_readexactly.assert_not_awaited()
            mock_trim_to.assert_not_called()
        else:
            mock_readexactly.assert_awaited_once_with(size)
            mock_trim_to.assert_called_once_with(size)
            assert len(buffer_manager.buffer) == size

    @patch(
        "asyncio.StreamReader.readexactly",
        side_effect=asyncio.IncompleteReadError(bytearray(), expected=7),
    )
    async def test_ensure_buffer_with_incomplete_read(
        self, mock_readexactly, buffer_manager: BufferManager
    ) -> None:
        """Test ensuring buffer size with incomplete read.

        Ensures that a ReadError is raised when the read is incomplete.
        """
        with pytest.raises(
            ReadError, match="Incomplete read. Tried to read 5 additional bytes"
        ):
            await buffer_manager.ensure_buffer(5)

        mock_readexactly.assert_awaited_once_with(5)

    @patch("asyncio.StreamReader.readexactly", side_effect=asyncio.CancelledError())
    async def test_ensure_buffer_with_cancelled_error(
        self, mock_readexactly, buffer_manager: BufferManager, caplog
    ) -> None:
        """Test ensuring buffer size with cancelled error.

        Ensures that CancelledError is raised and logged when the read is cancelled.
        """
        with pytest.raises(asyncio.CancelledError), caplog.at_level(logging.DEBUG):
            await buffer_manager.ensure_buffer(5)

        assert "Read operation cancelled while ensuring buffer" in caplog.text
        mock_readexactly.assert_awaited_once_with(5)

    @patch("asyncio.StreamReader.readexactly", side_effect=OSError())
    async def test_ensure_buffer_with_unexpected_error(
        self, mock_readexactly, buffer_manager: BufferManager
    ) -> None:
        """Test ensuring buffer size with unexpected error.

        Ensures that OSError is raised when an unexpected error occurs.
        """
        with pytest.raises(
            OSError, match="Serial connection broken while trying to ensure 5 bytes"
        ):
            await buffer_manager.ensure_buffer(5)

        mock_readexactly.assert_awaited_once_with(5)

    async def test_consume(self, buffer_manager: BufferManager) -> None:
        """Test consuming bytes from the buffer.

        Ensures that bytes are removed from the buffer as expected.
        """
        buffer_manager.buffer.extend(bytearray(b"\x00\x01"))
        assert len(buffer_manager.buffer) == 2
        await buffer_manager.consume(2)
        assert len(buffer_manager.buffer) == 0

    async def test_peek(self, buffer_manager: BufferManager) -> None:
        """Test peeking bytes from the buffer.

        Ensures that peeking returns the correct bytes without consuming them.
        """
        buffer_manager.buffer.extend(bytearray(b"\x00\x01\x02"))
        peeked_data = await buffer_manager.peek(2)
        assert len(peeked_data) == 2
        assert peeked_data == bytearray(b"\x00\x01")
        assert len(buffer_manager.buffer) == 3

    @patch("pyplumio.stream.BufferManager.peek")
    @patch("pyplumio.stream.BufferManager.consume")
    async def test_read(
        self, mock_consume, mock_peek, buffer_manager: BufferManager
    ) -> None:
        """Test reading bytes from the buffer.

        Ensures that reading calls peek and consume appropriately.
        """
        await buffer_manager.read(2)
        mock_peek.assert_awaited_once_with(2)
        mock_consume.assert_awaited_once_with(2)

    def test_seek_to(self, buffer_manager: BufferManager) -> None:
        """Test seeking to a delimiter in the buffer.

        Ensures that the buffer is trimmed up to the delimiter.
        """
        buffer_manager.buffer.extend(bytearray(b"\x00\x01\x02\x03\x04"))
        assert buffer_manager.seek_to(2) is True
        assert len(buffer_manager.buffer) == 3

    def test_trim_to(self, buffer_manager: BufferManager) -> None:
        """Test trimming the buffer to a specific size.

        Ensures that the buffer is trimmed to the correct length.
        """
        buffer_manager.buffer.extend(bytearray(b"\x00\x01\x02\x03\x04"))
        buffer_manager.trim_to(3)
        assert len(buffer_manager.buffer) == 3
        assert buffer_manager.buffer == bytearray(b"\x02\x03\x04")

    @patch("asyncio.StreamReader.read", return_value=bytearray(b"\x00\x01\x02"))
    @patch("pyplumio.stream.BufferManager.trim_to")
    async def test_fill(
        self, mock_trim_to, mock_read, buffer_manager: BufferManager
    ) -> None:
        """Test filling the buffer with data.

        Ensures that the buffer is filled and trimmed as expected.
        """
        await buffer_manager.fill()
        mock_read.assert_awaited_once_with(MAX_FRAME_LENGTH)
        mock_trim_to.assert_called_once_with(DEFAULT_BUFFER_SIZE)
        assert len(buffer_manager.buffer) == 3

    @patch("asyncio.StreamReader.read", side_effect=asyncio.CancelledError())
    async def test_fill_with_cancelled_error(
        self, mock_read, buffer_manager: BufferManager, caplog
    ) -> None:
        """Test filling the buffer with cancelled error.

        Ensures that CancelledError is raised and logged when the read is cancelled.
        """
        with caplog.at_level(logging.DEBUG), pytest.raises(asyncio.CancelledError):
            await buffer_manager.fill()

        mock_read.assert_awaited_once_with(MAX_FRAME_LENGTH)
        assert "Read operation cancelled while filling read buffer." in caplog.text

    @patch("asyncio.StreamReader.read", side_effect=OSError())
    async def test_fill_with_unexpected_error(
        self, mock_read, buffer_manager: BufferManager, caplog
    ) -> None:
        """Test filling the buffer with unexpected error.

        Ensures that OSError is raised when an unexpected error occurs.
        """
        with pytest.raises(
            OSError, match="Serial connection broken while filling read buffer"
        ):
            await buffer_manager.fill()

        mock_read.assert_awaited_once_with(MAX_FRAME_LENGTH)

    @patch("asyncio.StreamReader.read", return_value=b"")
    async def test_fill_with_broken_connection(
        self, mock_read, buffer_manager: BufferManager, caplog
    ) -> None:
        """Test filling the buffer with broken connection.

        Ensures that OSError is raised and logged when the connection is broken.
        """
        with (
            pytest.raises(OSError, match="Serial connection broken"),
            caplog.at_level(logging.DEBUG),
        ):
            await buffer_manager.fill()

        assert "Stream ended while filling read buffer." in caplog.text
        mock_read.assert_awaited_once_with(MAX_FRAME_LENGTH)


class TestFrameReader:
    """Tests for FrameReader class.

    Verifies reading, error handling, and frame validation.
    """

    @patch("asyncio.StreamReader.read", return_value=(b"\x00\x68"))
    @patch(
        "asyncio.StreamReader.readexactly",
        side_effect=(b"\x0c\x00\x00\x56\x30\x05", b"\x31\xff\x00\xc9\x16"),
    )
    async def test_read(
        self, mock_readexactly, mock_read, frame_reader: FrameReader
    ) -> None:
        """Test reading a frame.

        Checks correct parsing and field extraction from a frame.
        """
        frame = await frame_reader.read()
        assert isinstance(frame, EcomaxParametersRequest)
        assert frame.frame_type == FrameType.REQUEST_ECOMAX_PARAMETERS
        assert frame.sender == DeviceType.ECONET
        assert frame.econet_type == ECONET_TYPE
        assert frame.recipient == DeviceType.ALL
        assert frame.message == b"\xff\x00"
        assert frame.econet_version == ECONET_VERSION
        assert mock_read.call_count == 1
        mock_read.assert_has_calls([call(MAX_FRAME_LENGTH)])
        assert mock_readexactly.call_count == 2
        mock_readexactly.assert_has_calls([call(6), call(5)])

    @patch("asyncio.StreamReader.read", return_value=False)
    async def test_broken_connection(
        self, mock_read, frame_reader: FrameReader
    ) -> None:
        """Test broken connection.

        Ensures OSError is raised for empty read buffer.
        """
        with pytest.raises(OSError, match="Serial connection broken"):
            await frame_reader.read()

        mock_read.assert_awaited_once()

    @patch(
        "asyncio.StreamReader.readexactly",
        side_effect=asyncio.IncompleteReadError(bytearray(), expected=7),
    )
    async def test_incomplete_header(
        self, mock_readexactly, frame_reader: FrameReader, read_frame_start
    ) -> None:
        """Test incomplete header.

        Ensures ReadError is raised for incomplete frame header.
        """
        with pytest.raises(ReadError, match="Incomplete read"):
            await frame_reader.read()

        read_frame_start.assert_awaited_once()
        mock_readexactly.assert_awaited_once_with(6)

    @patch("asyncio.StreamReader.readexactly", return_value=b"\x03\x00\x00\x56\x30\x05")
    async def test_unexpected_frame_length(
        self, mock_readexactly, frame_reader: FrameReader, read_frame_start
    ) -> None:
        """Test unexpected frame length.

        Ensures ReadError is raised for unexpected frame length.
        """
        with pytest.raises(ReadError, match="Unexpected frame length"):
            await frame_reader.read()

        read_frame_start.assert_awaited_once()
        mock_readexactly.assert_awaited_once_with(6)

    @patch(
        "asyncio.StreamReader.readexactly",
        side_effect=(
            b"\x0c\x00\x00\x56\x30\x05",
            asyncio.IncompleteReadError(bytearray(), 10),
        ),
        new_callable=AsyncMock,
    )
    async def test_incomplete_frame(
        self, mock_readexactly, frame_reader: FrameReader, read_frame_start
    ) -> None:
        """Test incomplete frame.

        Ensures ReadError is raised for incomplete frame data.
        """
        with pytest.raises(ReadError, match="Incomplete read"):
            await frame_reader.read()

        read_frame_start.assert_awaited_once()
        mock_readexactly.assert_has_calls([call(6), call(5)])

    @pytest.mark.parametrize(
        ("target", "expected_exception", "error_pattern"),
        [
            ("asyncio.StreamReader.readexactly", OSError, "Serial connection broken"),
            ("asyncio.StreamReader.read", OSError, "Serial connection broken"),
            ("asyncio.StreamReader.readexactly", asyncio.CancelledError, None),
            ("asyncio.StreamReader.read", asyncio.CancelledError, None),
        ],
    )
    async def test_read_exceptions(
        self,
        frame_reader: FrameReader,
        read_frame_start,
        target: str,
        expected_exception: type[Exception],
        error_pattern: str,
    ) -> None:
        """Test read exceptions."""
        with (
            patch(target, side_effect=expected_exception()),
            pytest.raises(expected_exception, match=error_pattern),
        ):
            await frame_reader.read()

    @patch(
        "asyncio.StreamReader.readexactly",
        side_effect=(b"\x0c\x00\x00\x56\x30\x05", b"\x31\xfe\x00\xc9\x16"),
    )
    async def test_incorrect_checksum(
        self, mock_readexactly, frame_reader: FrameReader, read_frame_start
    ) -> None:
        """Test incorrect checksum.

        Ensures ChecksumError is raised for invalid checksum.
        """
        with pytest.raises(ChecksumError, match="Incorrect frame checksum"):
            await frame_reader.read()

        read_frame_start.assert_awaited_once()
        mock_readexactly.assert_has_calls([call(6), call(5)])

    @patch(
        "asyncio.StreamReader.read",
        return_value=b"\x68\x0a\x00\x10\x56\x30\x05\x01\x10\x16",
    )
    async def test_unknown_recipient(
        self, mock_read, frame_reader: FrameReader
    ) -> None:
        """Test unknown recipient.

        Verifies that the reader returns None when the recipient address
        in the frame is not recognized as a valid device.
        """
        result = await frame_reader.read()
        assert result is None
        mock_read.assert_awaited_once_with(MAX_FRAME_LENGTH)

    @patch(
        "asyncio.StreamReader.read",
        return_value=b"\x68\x0a\x00\x00\x10\x30\x05\x01\x46\x16",
    )
    async def test_unknown_sender(self, mock_read, frame_reader: FrameReader) -> None:
        """Test unknown sender.

        Verifies that an UnknownDeviceError is raised when the sender
        address in the frame does not match any known device types.
        """
        with pytest.raises(UnknownDeviceError, match="Unknown sender"):
            await frame_reader.read()

        mock_read.assert_awaited_once_with(MAX_FRAME_LENGTH)
