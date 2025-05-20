"""Contains a frame reader and writer classes."""

from __future__ import annotations

import asyncio
from asyncio import IncompleteReadError, StreamReader, StreamWriter
import logging
from typing import Final, NamedTuple

from pyplumio.const import DeviceType
from pyplumio.devices import is_known_device_type
from pyplumio.exceptions import ChecksumError, ReadError, UnknownDeviceError
from pyplumio.frames import (
    DELIMITER_SIZE,
    FRAME_START,
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

READER_CHUNK_SIZE: Final = 1000

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


class Header(NamedTuple):
    """Represents a frame header."""

    frame_length: int
    recipient: int
    sender: int
    econet_type: int
    econet_version: int


class FrameReader:
    """Represents a frame reader."""

    __slots__ = ("_buffer", "_reader")

    _buffer: bytearray
    _reader: StreamReader

    def __init__(self, reader: StreamReader) -> None:
        """Initialize a new frame reader."""
        self._buffer = bytearray()
        self._reader = reader

    async def _ensure_buffer(self, size: int) -> None:
        """Ensure the internal buffer size."""
        bytes_to_read = size - len(self._buffer)
        if bytes_to_read > 0:
            try:
                data = await self._reader.readexactly(bytes_to_read)
                self._buffer.extend(data)
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

    async def _consume_buffer(self, size: int) -> bytearray:
        """Ensure and consume the internal buffer."""
        await self._ensure_buffer(size)
        try:
            return self._buffer[:size]
        finally:
            self._buffer = self._buffer[size:]

    async def _read_header(self) -> Header:
        """Locate and read a frame header.

        Raise pyplumio.ReadError if header size is too small and
        OSError if serial connection is broken.
        """
        start_index = -1
        while True:
            if self._buffer:
                start_index = self._buffer.find(FRAME_START)

            if start_index != -1:
                self._buffer = self._buffer[start_index:]
                await self._ensure_buffer(HEADER_SIZE)
                header_bytes = self._buffer[:HEADER_SIZE]
                return Header(*struct_header.unpack_from(header_bytes)[DELIMITER_SIZE:])

            try:
                chunk = await self._reader.read(READER_CHUNK_SIZE)
            except asyncio.CancelledError:
                _LOGGER.debug("Read operation cancelled while searching for header.")
                raise
            except Exception as e:
                raise OSError(
                    f"Serial connection broken while reading header chunk: {e}"
                ) from e

            if not chunk:
                _LOGGER.debug("Stream ended while searching for frame header.")
                raise OSError(
                    "Serial connection broken: stream ended while searching for header"
                )

            self._buffer.extend(chunk)

    @timeout(READER_TIMEOUT)
    async def read(self) -> Frame | None:
        """Read the frame and return corresponding handler object.

        Raise pyplumio.UnknownDeviceError when sender device has an
        unknown address, raise pyplumio.ReadError on unexpected frame
        length or incomplete frame, raise pyplumio.ChecksumError on
        incorrect frame checksum.
        """
        header = await self._read_header()
        frame_length, recipient, sender, econet_type, econet_version = header
        frame_bytes = await self._consume_buffer(frame_length)

        if recipient not in (DeviceType.ECONET, DeviceType.ALL):
            # Not an intended recipient, ignore the frame.
            return None

        if not is_known_device_type(sender):
            raise UnknownDeviceError(f"Unknown sender type ({sender})")

        if frame_length > MAX_FRAME_LENGTH or frame_length < MIN_FRAME_LENGTH:
            raise ReadError(
                f"Unexpected frame length ({frame_length}), expected between "
                f"{MIN_FRAME_LENGTH} and {MAX_FRAME_LENGTH}"
            )

        if (checksum := bcc(frame_bytes[:-2])) and checksum != frame_bytes[-2]:
            raise ChecksumError(
                f"Incorrect frame checksum: calculated {checksum}, "
                f"expected {frame_bytes[-2]}. "
                f"Frame data: {frame_bytes.hex()}"
            )

        payload_bytes = frame_bytes[HEADER_SIZE : frame_length - 2]

        frame = await Frame.create(
            frame_type=payload_bytes[0],
            recipient=DeviceType(recipient),
            sender=DeviceType(sender),
            econet_type=econet_type,
            econet_version=econet_version,
            message=payload_bytes[1:],
        )
        _LOGGER.debug("Received frame: %s, bytes: %s", frame, frame_bytes.hex())

        return frame


__all__ = ["FrameReader", "FrameWriter"]
