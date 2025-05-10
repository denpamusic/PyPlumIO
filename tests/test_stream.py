"""Contains tests for the frame reader and writer classes."""

import asyncio
from collections.abc import Generator
from unittest.mock import AsyncMock, call, patch

import pytest

from pyplumio.const import DeviceType, FrameType
from pyplumio.exceptions import ChecksumError, ReadError, UnknownDeviceError
from pyplumio.frames import ECONET_TYPE, ECONET_VERSION
from pyplumio.frames.requests import EcomaxParametersRequest, ProgramVersionRequest
from pyplumio.stream import WRITER_TIMEOUT, FrameReader, FrameWriter


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


@pytest.fixture(name="frame_reader")
def fixture_frame_reader() -> Generator[FrameReader, None, None]:
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


class TestFrameReader:
    """Tests for FrameReader class.

    Verifies reading, error handling, and frame validation.
    """

    @patch("asyncio.StreamReader.read", side_effect=(b"\x00", b"\x68"))
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
        mock_read.call_count == 2
        mock_read.assert_has_calls([call(1), call(1)])
        mock_readexactly.call_count == 2
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
        with pytest.raises(ReadError, match="Incomplete header"):
            await frame_reader.read()

        read_frame_start.assert_awaited_once()
        mock_readexactly.assert_awaited_once_with(6)

    @patch(
        "asyncio.StreamReader.readexactly", side_effect=(b"\x03\x00\x00\x56\x30\x05",)
    )
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
        with pytest.raises(ReadError, match="Incomplete frame"):
            await frame_reader.read()

        read_frame_start.assert_awaited_once()
        mock_readexactly.assert_has_calls([call(6), call(5)])

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
        "asyncio.StreamReader.readexactly", side_effect=(b"\x0c\x00\x10\x56\x30\x05",)
    )
    async def test_unknown_recipient(
        self, mock_readexactly, frame_reader: FrameReader, read_frame_start
    ) -> None:
        """Test unknown recipient.

        Verifies that the reader returns None when the recipient address
        in the frame is not recognized as a valid device.
        """
        result = await frame_reader.read()
        assert result is None
        read_frame_start.assert_awaited_once()
        mock_readexactly.assert_awaited_once_with(6)

    @patch(
        "asyncio.StreamReader.readexactly", side_effect=(b"\x0c\x00\x00\x10\x30\x05",)
    )
    async def test_unknown_sender(
        self, mock_readexactly, frame_reader: FrameReader, read_frame_start
    ) -> None:
        """Test unknown sender.

        Verifies that an UnknownDeviceError is raised when the sender
        address in the frame does not match any known device types.
        """
        with pytest.raises(UnknownDeviceError, match="Unknown sender"):
            await frame_reader.read()

        read_frame_start.assert_awaited_once()
        mock_readexactly.assert_awaited_once_with(6)
