"""Contains a frame reader and writer classes."""

from __future__ import annotations

import asyncio
from asyncio import IncompleteReadError, StreamReader, StreamWriter
import logging
from typing import Final, NamedTuple

from pyplumio.const import DeviceType
from pyplumio.devices import is_known_device_type
from pyplumio.exceptions import ChecksumError, ReadError, UnknownDeviceError
from pyplumio.frames import FRAME_START, Frame, bcc, struct_header
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

    def __init__(self, writer: StreamWriter):
        """Initialize a new frame writer."""
        self._writer = writer

    @timeout(WRITER_TIMEOUT)
    async def write(self, frame: Frame) -> None:
        """Send the frame and wait until send buffer is empty."""
        self._writer.write(frame.bytes)
        await self._writer.drain()
        _LOGGER.debug("Sent frame: %s", frame)

    async def close(self) -> None:
        """Close the frame writer."""
        try:
            self._writer.close()
            await self.wait_closed()
        except (OSError, asyncio.TimeoutError):
            _LOGGER.exception("Unexpected error while closing the writer")

    @timeout(WRITER_TIMEOUT)
    async def wait_closed(self) -> None:
        """Wait until the frame writer is closed."""
        await self._writer.wait_closed()


class Header(NamedTuple):
    """Represents a frame header."""

    bytes: bytes
    frame_start: int
    frame_length: int
    recipient: int
    sender: int
    econet_type: int
    econet_version: int


class FrameReader:
    """Represents a frame reader."""

    __slots__ = ("_reader",)

    _reader: StreamReader

    def __init__(self, reader: StreamReader):
        """Initialize a new frame reader."""
        self._reader = reader

    async def _read_header(self) -> Header:
        """Locate and read a frame header.

        Raise pyplumio.ReadError if header size is too small and
        OSError if serial connection is broken.
        """
        while buffer := await self._reader.read(1):
            if FRAME_START not in buffer:
                continue

            buffer += await self._reader.read(struct_header.size - 1)
            if len(buffer) < struct_header.size:
                raise ReadError(f"Header can't be less than {struct_header.size} bytes")

            return Header(buffer, *struct_header.unpack_from(buffer))

        raise OSError("Serial connection broken")

    @timeout(READER_TIMEOUT)
    async def read(self) -> Frame | None:
        """Read the frame and return corresponding handler object.

        Raise pyplumio.ReadError on unexpected frame length or
        incomplete frame and pyplumio. Raise ChecksumError on incorrect
        frame checksum.
        """
        (
            header_bytes,
            _,
            frame_length,
            recipient,
            sender,
            econet_type,
            econet_version,
        ) = await self._read_header()

        if recipient not in (DeviceType.ECONET, DeviceType.ALL):
            return None

        if not is_known_device_type(sender):
            raise UnknownDeviceError(f"Unknown sender type ({sender})")

        if frame_length > MAX_FRAME_LENGTH or frame_length < MIN_FRAME_LENGTH:
            raise ReadError(f"Unexpected frame length ({frame_length})")

        try:
            payload = await self._reader.readexactly(frame_length - struct_header.size)
        except IncompleteReadError as e:
            raise ReadError(
                "Got an incomplete frame while trying to read "
                + f"'{frame_length - struct_header.size}' bytes"
            ) from e

        if (checksum := bcc(header_bytes + payload[:-2])) and checksum != payload[-2]:
            raise ChecksumError(
                f"Incorrect frame checksum ({checksum} != {payload[-2]})"
            )

        frame = await Frame.create(
            frame_type=payload[0],
            recipient=DeviceType(recipient),
            sender=DeviceType(sender),
            econet_type=econet_type,
            econet_version=econet_version,
            message=payload[1:-2],
        )
        _LOGGER.debug("Received frame: %s", frame)

        return frame
