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

    __slots__ = ("_reader",)

    _reader: StreamReader

    def __init__(self, reader: StreamReader) -> None:
        """Initialize a new frame reader."""
        self._reader = reader

    async def _read_header(self) -> tuple[Header, bytes]:
        """Locate and read a frame header.

        Raise pyplumio.ReadError if header size is too small and
        OSError if serial connection is broken.
        """
        while buffer := await self._reader.read(DELIMITER_SIZE):
            if FRAME_START not in buffer:
                continue

            try:
                buffer += await self._reader.readexactly(HEADER_SIZE - DELIMITER_SIZE)
            except IncompleteReadError as e:
                raise ReadError(
                    f"Incomplete header, expected {e.expected} bytes"
                ) from e

            return Header(*struct_header.unpack_from(buffer)[DELIMITER_SIZE:]), buffer

        raise OSError("Serial connection broken")

    @timeout(READER_TIMEOUT)
    async def read(self) -> Frame | None:
        """Read the frame and return corresponding handler object.

        Raise pyplumio.UnknownDeviceError when sender device has an
        unknown address, raise pyplumio.ReadError on unexpected frame
        length or incomplete frame, raise pyplumio.ChecksumError on
        incorrect frame checksum.
        """
        header, buffer = await self._read_header()
        frame_length, recipient, sender, econet_type, econet_version = header

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

        try:
            buffer += await self._reader.readexactly(frame_length - HEADER_SIZE)
        except IncompleteReadError as e:
            raise ReadError(f"Incomplete frame, expected {e.expected} bytes") from e

        if (checksum := bcc(buffer[:-2])) and checksum != buffer[-2]:
            raise ChecksumError(
                f"Incorrect frame checksum: calculated {checksum}, "
                f"expected {buffer[-2]}. "
                f"Frame data: {buffer.hex()}"
            )

        frame = await Frame.create(
            frame_type=buffer[HEADER_SIZE],
            recipient=DeviceType(recipient),
            sender=DeviceType(sender),
            econet_type=econet_type,
            econet_version=econet_version,
            message=buffer[HEADER_SIZE + 1 : -2],
        )
        _LOGGER.debug("Received frame: %s, bytes: %s", frame, buffer.hex())

        return frame
