"""Contains a frame reader and writer classes."""

from __future__ import annotations

import asyncio
from asyncio import IncompleteReadError, StreamReader, StreamWriter
import logging
from typing import Final, NamedTuple, SupportsIndex

from pyplumio.const import DeviceType
from pyplumio.devices import is_known_device_type
from pyplumio.exceptions import ChecksumError, ReadError, UnknownDeviceError
from pyplumio.frames import (
    BCC_INDEX,
    DELIMITER_SIZE,
    FRAME_START,
    FRAME_TYPE_SIZE,
    HEADER_SIZE,
    Frame,
    bcc,
    struct_header,
)
from pyplumio.helpers.timeout import timeout

READER_TIMEOUT: Final = 10
WRITER_TIMEOUT: Final = 10

MIN_FRAME_LENGTH: Final = 10
MAX_FRAME_LENGTH: Final = 1000

DEFAULT_BUFFER_SIZE: Final = 5000

_LOGGER = logging.getLogger(__name__)


class FrameWriter:
    """Represents a frame writer."""

    __slots__ = ("_writer",)

    _writer: StreamWriter

    def __init__(self, writer: StreamWriter) -> None:
        """Initialize a new frame writer."""
        self._writer = writer

    @timeout(WRITER_TIMEOUT)
    async def write(self, frame: Frame) -> None:
        """Send the frame and wait until send buffer is empty."""
        self._writer.write(frame.bytes)
        await self._writer.drain()
        _LOGGER.debug("Sent frame: %s, bytes: %s", frame, frame.bytes)

    async def close(self) -> None:
        """Close the frame writer."""
        try:
            self._writer.close()
            await self.wait_closed()
        except (OSError, asyncio.TimeoutError):
            _LOGGER.exception(
                "Failed to close the frame writer due to an unexpected error"
            )

    @timeout(WRITER_TIMEOUT)
    async def wait_closed(self) -> None:
        """Wait until the frame writer is closed."""
        await self._writer.wait_closed()


class BufferManager:
    """Represents a buffered reader for reading frames."""

    __slots__ = ("_buffer", "_reader")

    _buffer: bytearray
    _reader: StreamReader

    def __init__(self, reader: StreamReader) -> None:
        """Initialize a new buffered reader."""
        self._buffer = bytearray()
        self._reader = reader

    async def ensure_buffer(self, size: int) -> None:
        """Ensure the internal buffer size."""
        bytes_to_read = size - len(self._buffer)
        if bytes_to_read <= 0:
            return None

        try:
            data = await self._reader.readexactly(bytes_to_read)
            self._buffer.extend(data)
            self.trim_to(size)
        except IncompleteReadError as e:
            raise ReadError(
                f"Incomplete read. Tried to read {bytes_to_read} additional bytes "
                f"to reach a total of {size}, but only {len(e.partial)} bytes were "
                "available from stream."
            ) from e
        except asyncio.CancelledError:
            _LOGGER.debug("Read operation cancelled while ensuring buffer")
            raise
        except Exception as e:
            raise OSError(
                f"Serial connection broken while trying to ensure {size} bytes: {e}"
            ) from e

    async def consume(self, size: int) -> None:
        """Consume the specified number of bytes from the buffer."""
        await self.ensure_buffer(size)
        self._buffer = self._buffer[size:]

    async def peek(self, size: int) -> bytearray:
        """Read the specified number of bytes without consuming them."""
        await self.ensure_buffer(size)
        return self._buffer[:size]

    async def read(self, size: int) -> bytearray:
        """Read the bytes from buffer or stream and consume them."""
        try:
            return await self.peek(size)
        finally:
            await self.consume(size)

    def seek_to(self, delimiter: SupportsIndex) -> bool:
        """Trim the buffer to the first occurrence of the delimiter.

        Returns True if the delimiter was found and trimmed, False otherwise.
        """
        if not self._buffer or (index := self._buffer.find(delimiter)) == -1:
            return False

        self._buffer = self._buffer[index:]
        return True

    def trim_to(self, size: int) -> None:
        """Trim buffer to size."""
        if len(self._buffer) > size:
            self._buffer = self._buffer[-size:]

    async def fill(self) -> None:
        """Fill the buffer with data from the stream."""
        try:
            chunk = await self._reader.read(MAX_FRAME_LENGTH)
        except asyncio.CancelledError:
            _LOGGER.debug("Read operation cancelled while filling read buffer.")
            raise
        except Exception as e:
            raise OSError(
                f"Serial connection broken while filling read buffer: {e}"
            ) from e

        if not chunk:
            _LOGGER.debug("Stream ended while filling read buffer.")
            raise OSError(
                "Serial connection broken: stream ended while filling read buffer"
            )

        self._buffer.extend(chunk)
        self.trim_to(DEFAULT_BUFFER_SIZE)

    @property
    def buffer(self) -> bytearray:
        """Return the internal buffer."""
        return self._buffer


class Header(NamedTuple):
    """Represents a frame header."""

    frame_length: int
    recipient: int
    sender: int
    econet_type: int
    econet_version: int


class FrameReader:
    """Represents a frame reader."""

    __slots__ = ("_buffer",)

    _buffer: BufferManager

    def __init__(self, reader: StreamReader) -> None:
        """Initialize a new frame reader."""
        self._buffer = BufferManager(reader)

    async def _read_header(self) -> Header:
        """Locate and read a frame header."""
        while True:
            if self._buffer.seek_to(FRAME_START):
                header_bytes = await self._buffer.peek(HEADER_SIZE)
                return Header(*struct_header.unpack_from(header_bytes)[DELIMITER_SIZE:])

            await self._buffer.fill()

    @timeout(READER_TIMEOUT)
    async def read(self) -> Frame | None:
        """Read the frame and return corresponding handler object."""
        header = await self._read_header()
        frame_length, recipient, sender, econet_type, econet_version = header

        if frame_length > MAX_FRAME_LENGTH or frame_length < MIN_FRAME_LENGTH:
            await self._buffer.consume(HEADER_SIZE)
            raise ReadError(
                f"Unexpected frame length ({frame_length}), expected between "
                f"{MIN_FRAME_LENGTH} and {MAX_FRAME_LENGTH}"
            )

        frame_bytes = await self._buffer.peek(frame_length)
        checksum = bcc(frame_bytes[:BCC_INDEX])
        if checksum != frame_bytes[BCC_INDEX]:
            await self._buffer.consume(HEADER_SIZE)
            raise ChecksumError(
                f"Incorrect frame checksum: calculated {checksum}, "
                f"expected {frame_bytes[BCC_INDEX]}. Frame data: {frame_bytes.hex()}"
            )

        await self._buffer.consume(frame_length)
        if recipient not in (DeviceType.ECONET, DeviceType.ALL):
            _LOGGER.debug(
                "Skipping frame intended for different recipient (%s)", recipient
            )
            return None

        if not is_known_device_type(sender):
            raise UnknownDeviceError(f"Unknown sender type ({sender})")

        payload_bytes = frame_bytes[HEADER_SIZE:BCC_INDEX]
        frame = await Frame.create(
            frame_type=payload_bytes[0],
            recipient=DeviceType(recipient),
            sender=DeviceType(sender),
            econet_type=econet_type,
            econet_version=econet_version,
            message=payload_bytes[FRAME_TYPE_SIZE:],
        )
        _LOGGER.debug("Received frame: %s, bytes: %s", frame, frame_bytes.hex())

        return frame


__all__ = ["FrameReader", "FrameWriter"]
